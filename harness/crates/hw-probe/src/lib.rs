//! `hw-probe` — peak VRAM, peak system RAM, temperature and throttle, around any workload.
//!
//! Built for brief §14 item 2 (W1 + W2), which says in as many words: *"Report peak VRAM **and**
//! peak system RAM as a hard limit — nothing in the family measures either today, so budget
//! building the probe as part of this workstream."* That is accurate. Claudette's `hw.rs` shells
//! out to `nvidia-smi --query-gpu=memory.total` and reads **installed** VRAM once; it has no peak,
//! no system-RAM probe and no temperature probe. Nothing in `harness/crates/` touches VRAM at all.
//!
//! # What it is for
//!
//! Every measured claim W1 and W2 owe depends on this instrument existing first:
//!
//! - the concurrency ceiling — *"find the point where the machine becomes unstable and report it
//!   as a hard limit, not a tuning suggestion"*;
//! - KV-cache growth under full residency;
//! - model-swap cost;
//! - whether a second model can sit beside the champion's 13.6 GB for W6's independent reviewer.
//!
//! # 🚨 What this instrument cannot see, stated up front
//!
//! **A peak over samples is a lower bound on the true peak.** Nothing here is a high-water mark
//! kept by the driver; it is a maximum over what was observed. An allocation that rises and falls
//! between two samples is invisible, and the width of that blind window is
//! [`crate::sample::Cadence::max_gap_ms`] — reported beside every peak, never omitted. The GPU
//! series runs at ~100 ms and the host series at 1,000 ms (`typeperf`'s floor), so the two blind
//! windows differ by an order of magnitude and are reported separately.
//!
//! **`memory.used` is the whole card, not one process.** On this host
//! `nvidia-smi --query-compute-apps` returns `[N/A]` for every process's memory, so NVIDIA's own
//! tool cannot attribute VRAM. The discipline that follows is to measure a **baseline with the
//! model unloaded** and subtract; `hw-probe baseline` exists for that. Windows' per-process GPU
//! counters *can* attribute it, and `--per-process` turns them on — see [`host`].
//!
//! # Layout
//!
//! - [`gpu`] — the `nvidia-smi -lms` stream. ~100 ms.
//! - [`host`] — the `typeperf` stream: system RAM, and the per-process GPU counters. 1 s floor.
//! - [`sample`] — what a sample is and what an honest summary may claim of it.
//!
//! No third-party dependencies and no `unsafe`, matching the rest of the workspace.

pub mod gpu;
pub mod host;
pub mod sample;

use std::fmt::Write as _;
use std::process::{Child, Command, Stdio};
use std::time::Instant;

use sample::{Series, Stats, is_thermal, json_quote, throttle_reasons};

// ---------------------------------------------------------------------------
// Killing a stream
// ---------------------------------------------------------------------------

/// Kill a child **and everything it spawned**.
///
/// 🚨 **A closed pipe does not stop these children.** Observed here: `nvidia-smi … -lms 200 |
/// head -3` left `nvidia-smi` alive after `head` exited, and it had to be killed by hand. Windows
/// has no SIGPIPE for a child to inherit, so a probe that merely drops its end of the pipe leaks a
/// process that goes on querying the driver for the rest of the session — and, being a probe,
/// leaks one per measurement.
///
/// The tree, not the child, for the reason `w8-run`'s F57 fix records: a leaked grandchild both
/// wastes a core and keeps an inherited stdout handle open, which can hang the parent that is
/// waiting to see the pipe close.
pub fn kill_tree(child: &mut Child) -> bool {
    let ok = kill_tree_impl(child);
    let _ = child.kill();
    let _ = child.wait();
    ok
}

#[cfg(windows)]
fn kill_tree_impl(child: &mut Child) -> bool {
    // Spawned directly rather than through a shell, so MSYS cannot rewrite `/F` into `F:/`.
    Command::new("taskkill")
        .args(["/F", "/T", "/PID", &child.id().to_string()])
        .stdin(Stdio::null())
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .status()
        .map(|s| s.success())
        .unwrap_or(false)
}

#[cfg(unix)]
fn kill_tree_impl(child: &mut Child) -> bool {
    Command::new("kill")
        .args(["-9", &format!("-{}", child.id())])
        .stdin(Stdio::null())
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .status()
        .map(|s| s.success())
        .unwrap_or(false)
}

// ---------------------------------------------------------------------------
// The probe
// ---------------------------------------------------------------------------

/// What to sample.
#[derive(Debug, Clone)]
pub struct Config {
    pub gpu_interval_ms: u64,
    /// Seconds. `typeperf`'s own floor is 1 and this is clamped to it.
    pub host_interval_s: u64,
    pub gpu: bool,
    pub host: bool,
    /// Add the per-process and per-adapter GPU counters. Off by default: the wildcard expands to
    /// ~25 columns on an idle desktop, which is noise unless attribution is the question.
    pub per_process: bool,
    /// A label carried into the report, so a directory of runs can be told apart.
    pub label: String,
    /// The process a residency claim is about. Implies `per_process`.
    pub focus_pid: Option<u32>,
}

impl Default for Config {
    fn default() -> Config {
        Config {
            gpu_interval_ms: 100,
            host_interval_s: 1,
            gpu: true,
            host: true,
            per_process: false,
            label: String::new(),
            focus_pid: None,
        }
    }
}

/// A live measurement.
pub struct Probe {
    gpu: Option<gpu::GpuSource>,
    host: Option<host::HostSource>,
    started: Instant,
    config: Config,
    notes: Vec<String>,
    /// GPU samples already pulled off the channel by [`Probe::poll`]. They cannot be left in the
    /// channel — a full pipe stalls `nvidia-smi`, and a stalled sampler is a gap in the trace —
    /// so they are held here until [`Probe::stop`] merges them with the rest.
    pending: Vec<sample::Sample>,
}

impl Probe {
    /// Start sampling.
    ///
    /// A source that will not start is a **note**, not an error: a box with no NVIDIA card should
    /// still be able to report its peak RAM, and refusing the whole measurement because one of two
    /// instruments is missing is how a probe becomes something people work around.
    pub fn start(config: Config) -> Probe {
        let mut notes = Vec::new();
        let gpu = if config.gpu {
            match gpu::supported_metrics(gpu::GPU_METRICS) {
                Ok(m) => {
                    if m.len() != gpu::GPU_METRICS.len() {
                        let kept: Vec<&str> = m.iter().map(|d| d.key).collect();
                        notes.push(format!(
                            "nvidia-smi refused some fields; kept {}",
                            kept.join(",")
                        ));
                    }
                    match gpu::GpuSource::start(config.gpu_interval_ms, m) {
                        Ok(s) => Some(s),
                        Err(e) => {
                            notes.push(format!("gpu source off: {e}"));
                            None
                        }
                    }
                }
                Err(e) => {
                    notes.push(format!("gpu source off: {e}"));
                    None
                }
            }
        } else {
            None
        };
        let host = if config.host {
            let mut counters: Vec<String> =
                host::HOST_COUNTERS.iter().map(|(p, _, _)| p.to_string()).collect();
            // Naming a pid is a request for that pid's numbers, so it turns the wildcards on
            // rather than silently producing a report with nothing to attribute.
            if config.per_process || config.focus_pid.is_some() {
                counters.extend(host::GPU_WILDCARDS.iter().map(|s| s.to_string()));
            }
            if config.focus_pid.is_some() {
                counters.extend(host::PROC_WILDCARDS.iter().map(|s| s.to_string()));
            }
            match host::HostSource::start(config.host_interval_s, &counters) {
                Ok(s) => Some(s),
                Err(e) => {
                    notes.push(format!("host source off: {e}"));
                    None
                }
            }
        } else {
            None
        };
        Probe {
            gpu,
            host,
            started: Instant::now(),
            config,
            notes,
            pending: Vec::new(),
        }
    }

    pub fn elapsed_ms(&self) -> u64 {
        self.started.elapsed().as_millis() as u64
    }

    /// Pull whatever the sources have produced, so their pipes cannot fill. Call periodically
    /// during a long measurement; a full pipe would stall the child rather than lose samples, but
    /// a stalled `nvidia-smi` stops sampling, which is the same thing in the end.
    pub fn poll(&mut self) {
        if let Some(g) = &self.gpu {
            let mut v = Vec::new();
            g.drain(&mut v);
            self.pending.extend(v);
        }
        if let Some(h) = &mut self.host {
            h.drain();
        }
    }

    /// Add a note that will travel with the report — what was being done, what was loaded.
    pub fn note(&mut self, s: impl Into<String>) {
        self.notes.push(s.into());
    }

    /// Stop sampling and summarise.
    pub fn stop(mut self) -> Report {
        let wall_ms = self.elapsed_ms();
        let mut gpu_series = self.gpu.take().map(|g| g.stop());
        if let (Some(s), false) = (gpu_series.as_mut(), self.pending.is_empty()) {
            let mut merged = std::mem::take(&mut self.pending);
            merged.append(&mut s.samples);
            merged.sort_by_key(|x| x.t_ms);
            s.samples = merged;
        }
        let mut host_series = self.host.take().map(|h| h.stop());
        let mut proc_instance = None;
        if let (Some(pid), Some(hs)) = (self.config.focus_pid, host_series.as_mut()) {
            proc_instance = resolve_proc_instance(hs, pid);
            match &proc_instance {
                Some(inst) => {
                    // 375 `\Process(*)` columns become one process's three. Pruning here rather
                    // than at render keeps the written trace usable by hand; unpruned it is ~4 KB
                    // per second of run.
                    let prefix = format!("process.{inst}.");
                    hs.retain(|m| !m.key.starts_with("process.") || m.key.starts_with(&prefix));
                }
                None => {
                    self.notes.push(format!(
                        "pid {pid} had no \\Process instance — it did not exist when the probe \
                         started, or it ended before the first sample"
                    ));
                    hs.retain(|m| !m.key.starts_with("process."));
                }
            }
        }
        Report {
            label: self.config.label.clone(),
            wall_ms,
            gpu: gpu_series,
            host: host_series,
            notes: self.notes.clone(),
            child_status: None,
            focus_pid: self.config.focus_pid,
            proc_instance,
        }
    }
}

/// Find which `\Process(name#n)` instance is the given pid, via the `ID Process` counter.
///
/// Instance names are executable base names, so several processes share one and Windows
/// disambiguates with `#1`, `#2` suffixes whose assignment order is not documented and **can
/// change between typeperf runs**. Matching on the name would therefore attribute one Chrome
/// renderer's memory to another and never look wrong. `ID Process` is the only stable key.
fn resolve_proc_instance(host: &Series, pid: u32) -> Option<String> {
    for (i, m) in host.metrics.iter().enumerate() {
        if !m.key.ends_with(".id_process") {
            continue;
        }
        // A pid does not change during a run, so any sample answers — but `max` also skips the
        // blank readings typeperf emits for an instance that has gone away.
        if host.stats(i).max() == Some(pid as f64) {
            return Some(instance_of(&m.key));
        }
    }
    None
}

// ---------------------------------------------------------------------------
// The report
// ---------------------------------------------------------------------------

/// A finished measurement.
pub struct Report {
    pub label: String,
    pub wall_ms: u64,
    pub gpu: Option<Series>,
    pub host: Option<Series>,
    pub notes: Vec<String>,
    /// Exit code of the wrapped command, when the probe was run around one.
    pub child_status: Option<i32>,
    /// The process a residency claim is about. Without one, no residency claim is made.
    pub focus_pid: Option<u32>,
    /// Which `\Process(name#n)` instance that pid turned out to be.
    pub proc_instance: Option<String>,
}

impl Report {
    /// The focus process's **exact** peak working set, in bytes, and the rise in it across the
    /// probe's window.
    ///
    /// The first number is kernel-maintained and therefore a true peak — the only one in this
    /// crate. The second is what can honestly be attributed to *this* measurement, since the
    /// first covers the process's whole life. When a process was started by `hw-probe run` they
    /// are the same thing; when the probe was pointed at an already-running LM Studio they are
    /// not, and quoting the first as if it were the second would credit this workload with memory
    /// some earlier one used.
    pub fn focus_ws_peak_b(&self) -> Option<(f64, f64)> {
        let inst = self.proc_instance.as_ref()?;
        let s = self.host.as_ref()?;
        match s.stats_of(&format!("process.{inst}.working_set_peak"))? {
            Stats::Numeric { max, first, .. } => Some((max, max - first)),
            _ => None,
        }
    }
}

/// Why a series has no number to report — three different situations that must not read alike.
///
/// "The source was off", "the source ran and produced nothing" and "the run was over before the
/// source's first sample was due" call for three different responses from whoever is reading, and
/// a single `n/a` invites the wrong one. The third is the common case for `hw-probe run` around a
/// fast command: `typeperf` cannot sample below one second, so a 0.2 s command genuinely has no
/// host reading, and that is a property of the question, not a fault.
fn why_empty(series: &Option<Series>, wall_ms: u64) -> String {
    match series {
        None => "(source off or unavailable — see notes)".to_string(),
        Some(s) if s.samples.is_empty() && wall_ms < s.nominal_ms => format!(
            "(run lasted {wall_ms} ms; this source samples every {} ms)",
            s.nominal_ms
        ),
        Some(_) => "(source ran but produced no sample)".to_string(),
    }
}

/// `gpu_proc_mem.pid_8476_luid_….local_usage` → `pid_8476_luid_…`.
fn instance_of(key: &str) -> String {
    let mid = key.split_once('.').map(|(_, r)| r).unwrap_or(key);
    mid.rsplit_once('.').map(|(l, _)| l).unwrap_or(mid).to_string()
}

impl Report {
    fn stat(series: &Option<Series>, key: &str) -> Option<Stats> {
        series.as_ref().and_then(|s| s.stats_of(key))
    }

    pub fn peak_vram_mib(&self) -> Option<f64> {
        Self::stat(&self.gpu, "mem_used_mib").and_then(|s| s.max())
    }

    pub fn total_vram_mib(&self) -> Option<f64> {
        Self::stat(&self.gpu, "mem_total_mib").and_then(|s| s.max())
    }

    pub fn peak_temp_c(&self) -> Option<f64> {
        Self::stat(&self.gpu, "temp_c").and_then(|s| s.max())
    }

    /// Peak committed system memory, in bytes.
    ///
    /// Commit rather than working set: it is what the system has *promised*, so it is the quantity
    /// that has a hard limit to be measured against.
    pub fn peak_committed_b(&self) -> Option<f64> {
        Self::stat(&self.host, "mem.committed_bytes").and_then(|s| s.max())
    }

    pub fn commit_limit_b(&self) -> Option<f64> {
        Self::stat(&self.host, "mem.commit_limit").and_then(|s| s.max())
    }

    /// The lowest the system's available memory ever fell, in MiB.
    pub fn min_avail_mib(&self) -> Option<f64> {
        match Self::stat(&self.host, "mem.available_mbytes") {
            Some(Stats::Numeric { min, .. }) => Some(min),
            _ => None,
        }
    }

    /// The largest **Non Local Usage** reached by any single GPU process, with the instance it
    /// belongs to.
    ///
    /// 🚨 **This is not a residency verdict, and an early version of this crate claimed it was.**
    /// A 12-second idle baseline on this box — no model loaded, nothing running but the desktop —
    /// reported 15.9 MiB of Non Local usage and printed "NOT fully resident". It was reading
    /// Explorer and a browser: **ordinary desktop processes hold shared GPU memory all the time**,
    /// and a system-wide maximum can never distinguish that from a model spilling. Residency is a
    /// claim about *one process*, so it is only made when [`Report::focus_pid`] names one —
    /// see [`Report::focus_gpu_bytes`]. Without a pid this is reported as information and
    /// deliberately carries no judgement.
    pub fn peak_gpu_spill_b(&self) -> Option<(String, f64)> {
        let s = self.host.as_ref()?;
        let mut worst: Option<(String, f64)> = None;
        for (i, m) in s.metrics.iter().enumerate() {
            if m.key.ends_with(".non_local_usage") {
                if let Some(v) = s.stats(i).max() {
                    if worst.as_ref().is_none_or(|(_, w)| v > *w) {
                        worst = Some((instance_of(&m.key), v));
                    }
                }
            }
        }
        worst
    }

    /// Peak `local_usage` (resident VRAM) and `non_local_usage` (host-shared GPU memory) for the
    /// process named by [`Report::focus_pid`], summed over its adapter instances.
    ///
    /// A pid can appear more than once — once per adapter LUID — so summing rather than taking a
    /// maximum is what makes the number the process's whole footprint.
    ///
    /// 🚨 **`non_local` is NOT eviction, and this crate printed "NOT fully resident" off it until
    /// 2026-08-16.** F61 established that a *system-wide* Non Local total is not a residency
    /// verdict and required `--pid` before any verdict was made. The negative control that should
    /// have accompanied that fix was only run in session 19, and it falsifies the per-pid verdict
    /// too: **`gemma-4-e2b`, a 4.1 GiB model on a 16,311 MiB card with ~13 GiB free, reports
    /// 2,290 MiB non-local** — 5.5× what the champion reports at 65k, while it cannot possibly be
    /// evicting anything. Non Local counts host memory the process has committed to the GPU
    /// address space, which llama.cpp allocates by design (staging buffers, and for this
    /// architecture the host-side per-layer embeddings), pressure or no pressure.
    ///
    /// So the pair is reported and **no verdict is derived from it**. The instrument that *can*
    /// settle residency is throughput: a model genuinely streaming hundreds of MiB per token over
    /// PCIe 3.0 x8 cannot hold 54–76 tok/s decode, and the champion does.
    pub fn focus_gpu_bytes(&self) -> Option<(f64, f64)> {
        let pid = self.focus_pid?;
        let s = self.host.as_ref()?;
        let prefix = format!("gpu_proc_mem.pid_{pid}_");
        let mut local = 0.0;
        let mut non_local = 0.0;
        let mut seen = false;
        for (i, m) in s.metrics.iter().enumerate() {
            if !m.key.starts_with(&prefix) {
                continue;
            }
            let Some(v) = s.stats(i).max() else { continue };
            if m.key.ends_with(".local_usage") {
                local += v;
                seen = true;
            } else if m.key.ends_with(".non_local_usage") {
                non_local += v;
                seen = true;
            }
        }
        seen.then_some((local, non_local))
    }

    /// Was the card ever hot enough to slow itself down?
    pub fn thermal_throttled(&self) -> bool {
        self.gpu
            .as_ref()
            .map(|s| is_thermal(s.bits_seen("throttle")))
            .unwrap_or(false)
    }

    /// The widest gap between GPU samples: the window in which a spike would be missed.
    pub fn gpu_blind_window_ms(&self) -> u64 {
        self.gpu.as_ref().map(|s| s.cadence().max_gap_ms).unwrap_or(0)
    }

    pub fn host_blind_window_ms(&self) -> u64 {
        self.host.as_ref().map(|s| s.cadence().max_gap_ms).unwrap_or(0)
    }

    pub fn to_json(&self) -> String {
        let mut s = String::new();
        let _ = write!(
            s,
            "{{\"label\":{},\"wall_ms\":{}",
            json_quote(&self.label),
            self.wall_ms
        );
        if let Some(c) = self.child_status {
            let _ = write!(s, ",\"child_status\":{c}");
        }
        let _ = write!(s, ",\"headline\":{}", self.headline_json());
        if let Some(g) = &self.gpu {
            let _ = write!(s, ",\"gpu\":{}", g.to_json());
        }
        if let Some(h) = &self.host {
            let _ = write!(s, ",\"host\":{}", h.to_json());
        }
        let notes = self
            .notes
            .iter()
            .map(|n| json_quote(n))
            .collect::<Vec<_>>()
            .join(",");
        let _ = write!(s, ",\"notes\":[{notes}]}}");
        s
    }

    fn headline_json(&self) -> String {
        let opt = |v: Option<f64>| match v {
            Some(v) if v.fract() == 0.0 => format!("{}", v as i64),
            Some(v) => format!("{v:.1}"),
            None => "null".to_string(),
        };
        let reasons = self
            .gpu
            .as_ref()
            .map(|s| throttle_reasons(s.bits_seen("throttle")))
            .unwrap_or_default()
            .iter()
            .map(|r| format!("\"{r}\""))
            .collect::<Vec<_>>()
            .join(",");
        format!(
            "{{\"peak_vram_mib\":{},\"total_vram_mib\":{},\"peak_vram_pct\":{},\
             \"gpu_blind_window_ms\":{},\"peak_temp_c\":{},\"thermal_throttled\":{},\
             \"throttle_reasons\":[{}],\"peak_committed_b\":{},\"commit_limit_b\":{},\
             \"min_avail_mib\":{},\"host_blind_window_ms\":{},\
             \"peak_gpu_shared_b_systemwide\":{},\"focus_pid\":{},\
             \"focus_on_card_b\":{},\"focus_host_shared_b\":{},\
             \"focus_ws_peak_b_exact\":{},\"focus_ws_rise_b\":{}}}",
            opt(self.peak_vram_mib()),
            opt(self.total_vram_mib()),
            opt(self.peak_vram_pct()),
            self.gpu_blind_window_ms(),
            opt(self.peak_temp_c()),
            self.thermal_throttled(),
            reasons,
            opt(self.peak_committed_b()),
            opt(self.commit_limit_b()),
            opt(self.min_avail_mib()),
            self.host_blind_window_ms(),
            opt(self.peak_gpu_spill_b().map(|(_, v)| v)),
            self.focus_pid
                .map(|p| p.to_string())
                .unwrap_or_else(|| "null".to_string()),
            opt(self.focus_gpu_bytes().map(|(l, _)| l)),
            opt(self.focus_gpu_bytes().map(|(_, n)| n)),
            opt(self.focus_ws_peak_b().map(|(p, _)| p)),
            opt(self.focus_ws_peak_b().map(|(_, r)| r)),
        )
    }

    pub fn peak_vram_pct(&self) -> Option<f64> {
        match (self.peak_vram_mib(), self.total_vram_mib()) {
            (Some(u), Some(t)) if t > 0.0 => Some(u / t * 100.0),
            _ => None,
        }
    }

    /// The terminal summary. Every peak is printed with its blind window, because a peak without
    /// one invites being quoted as if it were exact.
    pub fn render(&self) -> String {
        let mut s = String::new();
        let _ = writeln!(
            s,
            "hw-probe{}  {:.1}s",
            if self.label.is_empty() {
                String::new()
            } else {
                format!(" [{}]", self.label)
            },
            self.wall_ms as f64 / 1000.0
        );
        match (self.peak_vram_mib(), self.total_vram_mib()) {
            (Some(u), Some(t)) => {
                let _ = writeln!(
                    s,
                    "  peak VRAM      {u:.0} / {t:.0} MiB ({:.1}%)   [sampled, blind window {} ms]",
                    u / t * 100.0,
                    self.gpu_blind_window_ms()
                );
            }
            _ => {
                let _ = writeln!(s, "  peak VRAM      n/a {}", why_empty(&self.gpu, self.wall_ms));
            }
        }
        if let Some(temp) = self.peak_temp_c() {
            let bits = self
                .gpu
                .as_ref()
                .map(|g| g.bits_seen("throttle"))
                .unwrap_or(0);
            let reasons = throttle_reasons(bits);
            let _ = writeln!(
                s,
                "  peak temp      {temp:.0} C   thermal throttle: {}   reasons seen: {}",
                if self.thermal_throttled() { "YES" } else { "no" },
                if reasons.is_empty() {
                    "none".to_string()
                } else {
                    reasons.join("+")
                }
            );
        }
        match (self.peak_committed_b(), self.commit_limit_b()) {
            (Some(c), Some(l)) if l > 0.0 => {
                let _ = writeln!(
                    s,
                    "  peak commit    {:.2} / {:.2} GiB ({:.1}%)   [sampled, blind window {} ms]",
                    c / 1024.0 / 1024.0 / 1024.0,
                    l / 1024.0 / 1024.0 / 1024.0,
                    c / l * 100.0,
                    self.host_blind_window_ms()
                );
            }
            _ => {
                let _ = writeln!(
                    s,
                    "  peak commit    n/a {}",
                    why_empty(&self.host, self.wall_ms)
                );
            }
        }
        if let Some(a) = self.min_avail_mib() {
            let _ = writeln!(s, "  min available  {a:.0} MiB");
        }
        match (self.focus_pid, self.focus_gpu_bytes()) {
            (Some(pid), Some((local, non_local))) => {
                let mib = |b: f64| b / 1024.0 / 1024.0;
                // No verdict is derived from `non_local` — see `focus_gpu_bytes`. It counts
                // host-shared GPU memory that llama.cpp commits by design, so a threshold on it
                // flags a model with 13 GiB of headroom just as loudly as one that is truly full.
                let _ = writeln!(
                    s,
                    "  pid {pid:<6}     peak {:.0} MiB on-card + {:.1} MiB host-shared \
                     (host-shared is not eviction — see focus_gpu_bytes)",
                    mib(local),
                    mib(non_local),
                );
            }
            (Some(pid), None) => {
                // The wildcard is resolved when typeperf starts, so a pid that appeared later has
                // no column at all. Saying so beats reporting it as zero spill.
                let _ = writeln!(
                    s,
                    "  pid {pid:<6}     no GPU counters — did it exist when the probe started, and \
                     was --per-process set?"
                );
            }
            (None, _) => {
                if let Some((who, v)) = self.peak_gpu_spill_b() {
                    let _ = writeln!(
                        s,
                        "  GPU shared     {:.1} MiB peak Non Local, largest single process ({who}) \
                         — system-wide, NOT a residency verdict; pass --pid for that",
                        v / 1024.0 / 1024.0
                    );
                }
            }
        }
        if let Some((peak, rise)) = self.focus_ws_peak_b() {
            let gib = |b: f64| b / 1024.0 / 1024.0 / 1024.0;
            let _ = writeln!(
                s,
                "  pid RAM        peak working set {:.2} GiB (EXACT — kernel high-water mark), \
                 +{:.2} GiB during this window",
                gib(peak),
                gib(rise)
            );
        }
        for (name, series) in [("gpu", &self.gpu), ("host", &self.host)] {
            if let Some(sr) = series {
                let c = sr.cadence();
                let _ = writeln!(
                    s,
                    "  {name} cadence   n={} nominal={} ms actual mean={:.0} ms min={} max={}",
                    c.n, c.nominal_ms, c.mean_gap_ms, c.min_gap_ms, c.max_gap_ms
                );
            }
        }
        for n in &self.notes {
            let _ = writeln!(s, "  note: {n}");
        }
        s
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use sample::{Agg, Metric, Reading, Sample};

    fn series(source: &str, keys: &[(&str, &str, Agg)], rows: &[(u64, &[f64])]) -> Series {
        Series {
            source: source.to_string(),
            metrics: keys
                .iter()
                .map(|(k, u, a)| Metric::new(*k, *u, *a))
                .collect(),
            samples: rows
                .iter()
                .map(|(t, vs)| Sample {
                    t_ms: *t,
                    device_ts: String::new(),
                    readings: vs.iter().map(|v| Reading::Measured(*v)).collect(),
                })
                .collect(),
            nominal_ms: 100,
        }
    }

    fn gpu_series(rows: &[(u64, &[f64])]) -> Series {
        series(
            "gpu",
            &[
                ("mem_used_mib", "MiB", Agg::Numeric),
                ("mem_total_mib", "MiB", Agg::Numeric),
                ("temp_c", "C", Agg::Numeric),
                ("throttle", "bitmask", Agg::Bitmask),
            ],
            rows,
        )
    }

    fn report(gpu: Option<Series>, host: Option<Series>) -> Report {
        Report {
            label: String::new(),
            wall_ms: 1000,
            gpu,
            host,
            notes: vec![],
            child_status: None,
            focus_pid: None,
            proc_instance: None,
        }
    }

    #[test]
    fn the_peak_is_the_maximum_and_the_blind_window_travels_with_it() {
        let r = report(
            Some(gpu_series(&[
                (0, &[585.0, 16311.0, 52.0, 1.0]),
                (100, &[14919.0, 16311.0, 61.0, 1.0]),
                (900, &[13000.0, 16311.0, 58.0, 1.0]),
            ])),
            None,
        );
        assert_eq!(r.peak_vram_mib(), Some(14919.0));
        assert_eq!(r.total_vram_mib(), Some(16311.0));
        assert!((r.peak_vram_pct().unwrap() - 91.46).abs() < 0.01);
        // 800 ms of blindness between the last two samples, and the render must say so.
        assert_eq!(r.gpu_blind_window_ms(), 800);
        assert!(r.render().contains("blind window 800 ms"), "{}", r.render());
    }

    #[test]
    fn an_idle_cards_gpu_idle_bit_is_not_reported_as_overheating() {
        let r = report(
            Some(gpu_series(&[(0, &[585.0, 16311.0, 52.0, 1.0])])),
            None,
        );
        assert!(!r.thermal_throttled());
        assert!(r.render().contains("thermal throttle: no"));
        // But the bit is still disclosed rather than hidden.
        assert!(r.render().contains("GpuIdle"));
    }

    #[test]
    fn a_thermal_slowdown_is_surfaced_even_though_it_ended() {
        // The point of OR-ing a bitmask: the card recovered by the last sample, and a "final
        // value" reading would report a clean run.
        let r = report(
            Some(gpu_series(&[
                (0, &[585.0, 16311.0, 52.0, 1.0]),
                (100, &[585.0, 16311.0, 88.0, 0x40 as f64]),
                (200, &[585.0, 16311.0, 60.0, 1.0]),
            ])),
            None,
        );
        assert!(r.thermal_throttled());
        assert_eq!(r.peak_temp_c(), Some(88.0));
        assert!(r.render().contains("thermal throttle: YES"));
    }

    fn two_pid_host() -> Series {
        series(
            "host",
            &[
                ("gpu_proc_mem.pid_1_luid_a_phys_0.local_usage", "bytes", Agg::Numeric),
                ("gpu_proc_mem.pid_1_luid_a_phys_0.non_local_usage", "bytes", Agg::Numeric),
                ("gpu_proc_mem.pid_22_luid_a_phys_0.local_usage", "bytes", Agg::Numeric),
                ("gpu_proc_mem.pid_22_luid_a_phys_0.non_local_usage", "bytes", Agg::Numeric),
            ],
            &[
                (0, &[1000.0, 0.0, 4_000_000.0, 0.0]),
                (1000, &[1000.0, 0.0, 4_000_000.0, 5_242_880.0]),
            ],
        )
    }

    #[test]
    fn an_idle_desktops_shared_memory_is_not_a_residency_verdict() {
        // The bug this pins: a 12-second idle baseline on this box, nothing loaded, reported
        // 15.9 MiB of Non Local usage from Explorer and a browser — and an earlier version of
        // `render` printed "NOT fully resident" over it. Without a pid there is no verdict.
        let r = report(None, Some(two_pid_host()));
        let out = r.render();
        assert!(out.contains("NOT a residency verdict"), "{out}");
        assert!(!out.contains("🚨 NOT fully resident"), "{out}");
        // The information is still there, and it names who.
        let (who, v) = r.peak_gpu_spill_b().unwrap();
        assert_eq!(who, "pid_22_luid_a_phys_0");
        assert_eq!(v, 5_242_880.0);
    }

    #[test]
    fn naming_a_pid_attributes_both_numbers_to_that_pid() {
        let mut r = report(None, Some(two_pid_host()));
        r.focus_pid = Some(1);
        assert_eq!(r.focus_gpu_bytes(), Some((1000.0, 0.0)));

        r.focus_pid = Some(22);
        assert_eq!(r.focus_gpu_bytes(), Some((4_000_000.0, 5_242_880.0)));
        let out = r.render();
        assert!(out.contains("on-card"), "{out}");
        assert!(out.contains("host-shared"), "{out}");
    }

    #[test]
    fn host_shared_memory_never_becomes_an_eviction_verdict() {
        // The bug this pins, and it outlived the F61 fix: `--pid` was treated as enough to turn
        // Non Local into "🚨 NOT fully resident". The live negative control says otherwise —
        // gemma-4-e2b, 4.1 GiB on a 16,311 MiB card with ~13 GiB free, reports 2,290 MiB
        // non-local. A model that cannot be evicting must not trip the alarm, so there is no
        // alarm to trip: the pair is reported and the reader is told what it is not.
        let mut r = report(None, Some(two_pid_host()));
        r.focus_pid = Some(22); // the pid WITH non-local usage
        let out = r.render();
        assert!(!out.contains("NOT fully resident"), "{out}");
        assert!(!out.contains("spilled"), "{out}");
        assert!(out.contains("not eviction"), "{out}");
    }

    #[test]
    fn a_pid_with_no_columns_says_so_rather_than_reporting_zero_spill() {
        // typeperf resolves its wildcards at start, so a process that appeared later has no
        // column. Reporting that as "0 bytes spilled" would be a clean bill of health for a
        // measurement that never happened.
        let mut r = report(None, Some(two_pid_host()));
        r.focus_pid = Some(999);
        assert_eq!(r.focus_gpu_bytes(), None);
        let out = r.render();
        assert!(out.contains("no GPU counters"), "{out}");
        assert!(!out.contains("fully resident"), "{out}");
    }

    #[test]
    fn a_pid_on_two_adapters_is_summed_not_maxed() {
        // One process gets one instance per adapter LUID. Its footprint is the sum; a max would
        // under-report a process using both.
        let host = series(
            "host",
            &[
                ("gpu_proc_mem.pid_7_luid_a_phys_0.local_usage", "bytes", Agg::Numeric),
                ("gpu_proc_mem.pid_7_luid_b_phys_0.local_usage", "bytes", Agg::Numeric),
            ],
            &[(0, &[100.0, 250.0])],
        );
        let mut r = report(None, Some(host));
        r.focus_pid = Some(7);
        assert_eq!(r.focus_gpu_bytes(), Some((350.0, 0.0)));
    }

    #[test]
    fn a_process_instance_is_resolved_by_pid_and_never_by_name() {
        // Two instances of the same executable. `lms#1` is not necessarily the second one
        // started, and the suffix order is not documented and can change between typeperf runs —
        // so matching a name would attribute one process's memory to the other, silently.
        let host = series(
            "host",
            &[
                ("process.lms.id_process", "", Agg::Numeric),
                ("process.lms.working_set_peak", "bytes", Agg::Numeric),
                ("process.lms#1.id_process", "", Agg::Numeric),
                ("process.lms#1.working_set_peak", "bytes", Agg::Numeric),
            ],
            &[
                (0, &[4242.0, 1_000_000.0, 8888.0, 9_000_000.0]),
                (1000, &[4242.0, 3_000_000.0, 8888.0, 9_000_000.0]),
            ],
        );
        assert_eq!(resolve_proc_instance(&host, 8888), Some("lms#1".to_string()));
        assert_eq!(resolve_proc_instance(&host, 4242), Some("lms".to_string()));
        assert_eq!(resolve_proc_instance(&host, 1), None);

        let mut r = report(None, Some(host));
        r.focus_pid = Some(4242);
        r.proc_instance = Some("lms".to_string());
        // Peak 3 MB, of which 2 MB arrived during the window.
        assert_eq!(r.focus_ws_peak_b(), Some((3_000_000.0, 2_000_000.0)));
        assert!(r.render().contains("EXACT — kernel high-water mark"));
    }

    #[test]
    fn the_exact_peak_and_the_windows_rise_are_reported_separately() {
        // A process that peaked before the probe started reports that older peak. Quoting it as
        // this workload's cost would credit this run with memory an earlier one used, so the rise
        // is carried beside it and is zero here.
        let host = series(
            "host",
            &[("process.lms.working_set_peak", "bytes", Agg::Numeric)],
            &[(0, &[8_000_000.0]), (1000, &[8_000_000.0])],
        );
        let mut r = report(None, Some(host));
        r.focus_pid = Some(1);
        r.proc_instance = Some("lms".to_string());
        assert_eq!(r.focus_ws_peak_b(), Some((8_000_000.0, 0.0)));
    }

    #[test]
    fn retain_prunes_metrics_and_readings_together() {
        // If the two got out of step, every column after the pruned one would be reported under
        // its neighbour's name — the same silent mis-alignment `gpu::parse_line` guards against.
        let mut s = series(
            "host",
            &[
                ("mem.available_mbytes", "MiB", Agg::Numeric),
                ("process.a.working_set", "bytes", Agg::Numeric),
                ("process.b.working_set", "bytes", Agg::Numeric),
            ],
            &[(0, &[100.0, 200.0, 300.0]), (1000, &[110.0, 210.0, 310.0])],
        );
        s.retain(|m| !m.key.starts_with("process.") || m.key.starts_with("process.b."));
        assert_eq!(s.metrics.len(), 2);
        assert_eq!(s.samples[0].readings.len(), 2);
        assert_eq!(s.stats_of("mem.available_mbytes").unwrap().max(), Some(110.0));
        assert_eq!(s.stats_of("process.b.working_set").unwrap().max(), Some(310.0));
        assert!(s.stats_of("process.a.working_set").is_none());
    }

    #[test]
    fn a_pid_prefix_does_not_match_a_longer_pid() {
        // `pid_1` must not absorb `pid_22`'s columns — the trailing underscore in the prefix is
        // the whole defence, and without it every single-digit pid would swallow its decade.
        let mut r = report(None, Some(two_pid_host()));
        r.focus_pid = Some(1);
        assert_eq!(r.focus_gpu_bytes(), Some((1000.0, 0.0)));
    }

    #[test]
    fn a_missing_gpu_source_renders_as_n_a_and_not_as_zero() {
        let r = report(None, None);
        assert_eq!(r.peak_vram_mib(), None);
        let out = r.render();
        assert!(out.contains("peak VRAM      n/a"), "{out}");
        assert!(!out.contains("0 / 0 MiB"));
    }

    #[test]
    fn the_three_ways_of_having_no_number_read_differently() {
        // "off", "ran and produced nothing", and "the run was shorter than one sample interval"
        // are three different things to do next, so they must not share a message.
        let off = report(None, None);
        assert!(off.render().contains("source off or unavailable"));

        // A 200 ms run against a source that samples once a second: expected, not a fault.
        let mut too_fast = report(None, Some(Series::new("host", vec![], 1000)));
        too_fast.wall_ms = 200;
        let out = too_fast.render();
        assert!(out.contains("run lasted 200 ms"), "{out}");
        assert!(out.contains("samples every 1000 ms"), "{out}");

        // A 30 s run that produced nothing anyway: that IS a fault.
        let mut broken = report(None, Some(Series::new("host", vec![], 1000)));
        broken.wall_ms = 30_000;
        assert!(broken.render().contains("produced no sample"));
    }

    #[test]
    fn the_json_headline_carries_nulls_rather_than_dropping_keys() {
        let r = report(None, None);
        let j = r.to_json();
        assert!(j.contains("\"peak_vram_mib\":null"), "{j}");
        assert!(j.contains("\"thermal_throttled\":false"));
    }
}
