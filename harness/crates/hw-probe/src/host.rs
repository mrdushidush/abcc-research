//! The host source: one long-lived `typeperf`, for system RAM and for the numbers `nvidia-smi`
//! cannot produce on this box.
//!
//! **Why `typeperf` and not an FFI call to `GlobalMemoryStatusEx`.** The workspace has no `unsafe`
//! anywhere and no third-party dependency that is not load-bearing (see `harness/Cargo.toml`).
//! `typeperf` is a Windows built-in that streams PDH counters as CSV to stdout — the same
//! long-lived-child shape [`crate::gpu`] already uses, so it costs one process and no new
//! vocabulary. Shelling out to PowerShell per sample was the alternative and it is a non-starter:
//! interpreter start-up alone is several hundred milliseconds.
//!
//! **🚨 Two limits of this source that change what may be claimed from it.**
//!
//! 1. **The floor is one second.** `-si` takes `[[hh:]mm:]ss`; `-si 0.25` is rejected outright.
//!    So the host series is an order of magnitude coarser than the GPU series, and a RAM spike
//!    inside a second is invisible to it. The two cadences are reported separately for exactly
//!    this reason — a single "sample interval" field in the output would be a lie about one of
//!    them.
//! 2. **Wildcards are resolved once, at start.** `\GPU Process Memory(*)\…` expands to the
//!    processes alive when `typeperf` starts, and a process that appears later never gets a
//!    column. **So the probe must be started after the thing it is measuring exists** — or, for a
//!    model load, against the server process rather than the loader, since the pid that holds the
//!    weights is the one that was already running.
//!
//! **What this source is here to answer that `nvidia-smi` cannot.** On this host
//! `nvidia-smi --query-compute-apps=pid,used_memory` returns `[N/A]` for every process and
//! `[Insufficient Permissions]` for most names — per-process VRAM attribution is simply not
//! available from the NVIDIA tool on a consumer WDDM driver. Windows' own GPU counters *do*
//! report it, per pid, and they additionally separate **Local Usage** (dedicated VRAM) from
//! **Non Local Usage** (the shared system memory a WDDM driver spills into). That second column
//! is the direct measurement of the residency question W1 exists to answer: a config that spills
//! is not resident, however good its `memory.used` looks.

use std::io::{BufRead, BufReader};
use std::process::{Child, Command, Stdio};
use std::sync::mpsc::{self, Receiver};
use std::thread::JoinHandle;
use std::time::Instant;

use crate::sample::{Agg, Metric, Reading, Sample, Series};

/// The fixed, non-wildcard counters: the system-RAM half of "peak VRAM *and* peak system RAM".
///
/// `Committed Bytes` against `Commit Limit` is the pair that states a hard limit — available
/// memory falls for benign reasons (the cache gives it back), whereas commit approaching the limit
/// is the condition under which allocations start failing.
pub const HOST_COUNTERS: &[(&str, &str, &str)] = &[
    (r"\Memory\Available MBytes", "avail_mib", "MiB"),
    (r"\Memory\Committed Bytes", "committed_b", "bytes"),
    (r"\Memory\Commit Limit", "commit_limit_b", "bytes"),
];

/// The wildcard counters, added by `--per-process`.
///
/// `Non Local Usage` is the spill column. `Dedicated Usage` on the adapter set is the cross-check
/// against `nvidia-smi`'s `memory.used`: two independent instruments reading the same quantity is
/// the cheapest defence there is against a units mistake.
pub const GPU_WILDCARDS: &[&str] = &[
    r"\GPU Process Memory(*)\Local Usage",
    r"\GPU Process Memory(*)\Non Local Usage",
    r"\GPU Adapter Memory(*)\Dedicated Usage",
    r"\GPU Adapter Memory(*)\Shared Usage",
];

/// The per-process RAM counters, added by `--pid`.
///
/// 🚨 **`Working Set Peak` is the one number in this crate that is not a sampled maximum.** The
/// kernel maintains it as a true high-water mark, so it catches a spike this probe's 1-second
/// cadence would step straight over. That asymmetry is worth stating wherever these numbers are
/// quoted: **peak RAM for a named process is exact; peak VRAM is a lower bound.** Nothing on this
/// stack offers the VRAM equivalent — NVML has no per-process high-water mark and WDDM does not
/// keep one either.
///
/// ⚠ It is also a peak over the **process's whole life**, not over the probe's window. A process
/// that peaked before the probe started reports that older peak, so the honest reading is the
/// *rise* between the first and last sample — which is why `Working Set` is captured beside it.
///
/// `ID Process` is here because `\Process(*)` instances are keyed by **executable name**, and
/// duplicates get `name#1`, `name#2` suffixes in an order nothing documents. The pid is the only
/// unambiguous way back to the process the caller meant.
pub const PROC_WILDCARDS: &[&str] = &[
    r"\Process(*)\Working Set Peak",
    r"\Process(*)\Working Set",
    r"\Process(*)\ID Process",
];

/// Split one PDH-CSV row into its quoted fields.
///
/// Unlike `nvidia-smi`'s output this really is quoted CSV, and the counter paths in the header
/// contain characters (`\`, `(`, `)`, `#`) that a split-on-comma would survive but that make the
/// quoting worth honouring properly. Doubled quotes inside a field are unescaped, per RFC 4180 —
/// no counter name has yet needed it, which is the point at which a hand-rolled parser usually
/// gets it wrong.
fn csv_fields(line: &str) -> Vec<String> {
    let mut out = Vec::new();
    let mut cur = String::new();
    let mut in_quotes = false;
    let mut chars = line.chars().peekable();
    while let Some(c) = chars.next() {
        match c {
            '"' if in_quotes => {
                if chars.peek() == Some(&'"') {
                    cur.push('"');
                    chars.next();
                } else {
                    in_quotes = false;
                }
            }
            '"' => in_quotes = true,
            ',' if !in_quotes => out.push(std::mem::take(&mut cur)),
            c => cur.push(c),
        }
    }
    out.push(cur);
    out
}

/// Turn a full counter path into the short key the JSON uses.
///
/// `\\DAVID\GPU Process Memory(pid_8476_luid_0x…_phys_0)\Local Usage` becomes
/// `gpu_proc_mem.pid_8476_luid_0x…_phys_0.local_usage`. The host name goes because it is constant
/// within a run and noisy in every line; the instance stays because it is the attribution.
fn key_of(path: &str) -> String {
    // Strip the `\\HOST` prefix, if any.
    let p = path.strip_prefix(r"\\").unwrap_or(path);
    let rest = match p.find('\\') {
        Some(i) if path.starts_with(r"\\") => &p[i..],
        _ => path,
    };
    let parts: Vec<&str> = rest.trim_start_matches('\\').split('\\').collect();
    let mut object = parts.first().copied().unwrap_or("").to_string();
    let counter = parts.get(1).copied().unwrap_or("");
    let mut instance = String::new();
    if let (Some(a), Some(b)) = (object.find('('), object.rfind(')')) {
        instance = object[a + 1..b].to_string();
        object = object[..a].to_string();
    }
    let slug = |s: &str| {
        s.chars()
            .map(|c| if c.is_ascii_alphanumeric() { c.to_ascii_lowercase() } else { '_' })
            .collect::<String>()
            .trim_matches('_')
            .to_string()
    };
    let object = match object.as_str() {
        "Memory" => "mem".to_string(),
        "GPU Process Memory" => "gpu_proc_mem".to_string(),
        "GPU Adapter Memory" => "gpu_adapter_mem".to_string(),
        other => slug(other),
    };
    if instance.is_empty() {
        format!("{object}.{}", slug(counter))
    } else {
        format!("{object}.{instance}.{}", slug(counter))
    }
}

/// A `typeperf` header row, turned into the series' metric list.
///
/// Column 0 is `(PDH-CSV 4.0)` — the timestamp column — and is dropped, exactly as `nvidia-smi`'s
/// timestamp is.
pub fn metrics_from_header(header: &str) -> Vec<Metric> {
    let f = csv_fields(header);
    f.iter()
        .skip(1)
        .map(|p| {
            let key = key_of(p);
            let unit = if key.ends_with("_mib") || key.contains("mbytes") {
                "MiB"
            } else if key.contains("usage") || key.ends_with("_b") || key.contains("bytes") || key.contains("limit") {
                "bytes"
            } else {
                ""
            };
            Metric::new(key, unit, Agg::Numeric)
        })
        .collect()
}

/// A `typeperf` header is the row whose first field is the PDH banner.
fn is_header(line: &str) -> bool {
    line.trim_start().starts_with("\"(PDH-CSV")
}

/// Turn one data row into a sample.
pub fn parse_line(metrics: &[Metric], line: &str, t_ms: u64) -> Option<Sample> {
    if is_header(line) || line.trim().is_empty() {
        return None;
    }
    let f = csv_fields(line);
    if f.len() != metrics.len() + 1 {
        return None;
    }
    // Data rows start with a quoted timestamp; the trailing chatter ("Exiting, please wait...")
    // does not, and would otherwise be one field long anyway.
    let ts = f[0].trim();
    if ts.is_empty() || !ts.starts_with(|c: char| c.is_ascii_digit()) {
        return None;
    }
    Some(Sample {
        t_ms,
        device_ts: ts.to_string(),
        readings: f[1..].iter().map(|c| Reading::parse(c)).collect(),
    })
}

/// A running `typeperf` stream.
pub struct HostSource {
    child: Child,
    reader: Option<JoinHandle<()>>,
    rx: Receiver<(u64, String)>,
    metrics: Vec<Metric>,
    samples: Vec<Sample>,
    nominal_ms: u64,
}

impl HostSource {
    /// Spawn the stream. `interval_s` is clamped to at least 1 — the tool's own floor, made
    /// explicit here rather than left to `typeperf` to reject at run time.
    pub fn start(interval_s: u64, counters: &[String]) -> Result<HostSource, String> {
        let interval_s = interval_s.max(1);
        let mut cmd = Command::new("typeperf");
        for c in counters {
            cmd.arg(c);
        }
        let mut child = cmd
            .arg("-si")
            .arg(interval_s.to_string())
            .stdin(Stdio::null())
            .stdout(Stdio::piped())
            .stderr(Stdio::null())
            .spawn()
            .map_err(|e| format!("could not start typeperf: {e}"))?;
        let stdout = child
            .stdout
            .take()
            .ok_or_else(|| "typeperf gave no stdout".to_string())?;
        let t0 = Instant::now();
        let (tx, rx) = mpsc::channel();
        let reader = std::thread::spawn(move || {
            for line in BufReader::new(stdout).lines().map_while(Result::ok) {
                if tx.send((t0.elapsed().as_millis() as u64, line)).is_err() {
                    break;
                }
            }
        });
        Ok(HostSource {
            child,
            reader: Some(reader),
            rx,
            // Empty until the header arrives — typeperf prints it only once it has opened every
            // counter, which is also the moment the wildcard set is fixed.
            metrics: Vec::new(),
            samples: Vec::new(),
            nominal_ms: interval_s * 1000,
        })
    }

    fn absorb(&mut self, t: u64, line: String) {
        if is_header(&line) {
            // The header can only arrive once; a second one would mean typeperf restarted its
            // counter set mid-stream, which would invalidate every column index already used.
            if self.metrics.is_empty() {
                self.metrics = metrics_from_header(&line);
            }
            return;
        }
        if self.metrics.is_empty() {
            return;
        }
        if let Some(s) = parse_line(&self.metrics, &line, t) {
            self.samples.push(s);
        }
    }

    /// Everything received so far. Cheap; safe to call in a poll loop.
    pub fn drain(&mut self) {
        while let Ok((t, line)) = self.rx.try_recv() {
            self.absorb(t, line);
        }
    }

    /// The columns, once the header has been seen. Empty before that.
    pub fn metrics(&self) -> &[Metric] {
        &self.metrics
    }

    /// Kill the stream and return everything it produced.
    pub fn stop(mut self) -> Series {
        self.drain();
        crate::kill_tree(&mut self.child);
        if let Some(h) = self.reader.take() {
            let _ = h.join();
        }
        while let Ok((t, line)) = self.rx.try_recv() {
            self.absorb(t, line);
        }
        Series {
            source: "host".to_string(),
            metrics: self.metrics,
            samples: self.samples,
            nominal_ms: self.nominal_ms,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    /// Captured from this host, 2026-08-16, verbatim.
    const HEADER: &str = "\"(PDH-CSV 4.0)\",\"\\\\DAVID\\Memory\\Available MBytes\",\"\\\\DAVID\\Memory\\Committed Bytes\"";
    const ROW: &str = "\"08/16/2026 10:36:10.260\",\"24493.000000\",\"9983746048.000000\"";

    #[test]
    fn the_real_captured_header_and_row_agree_on_arity() {
        let m = metrics_from_header(HEADER);
        assert_eq!(m.len(), 2);
        assert_eq!(m[0].key, "mem.available_mbytes");
        assert_eq!(m[0].unit, "MiB");
        assert_eq!(m[1].key, "mem.committed_bytes");
        assert_eq!(m[1].unit, "bytes");

        let s = parse_line(&m, ROW, 1000).expect("real row must parse");
        assert_eq!(s.device_ts, "08/16/2026 10:36:10.260");
        assert_eq!(s.readings[0], Reading::Measured(24493.0));
        assert_eq!(s.readings[1], Reading::Measured(9_983_746_048.0));
    }

    #[test]
    fn a_gpu_wildcard_instance_keeps_its_pid() {
        // The instance name *is* the attribution — losing it would leave a column of numbers with
        // nothing to attach them to, which is the state `nvidia-smi` leaves this host in.
        let path = r"\\DAVID\GPU Process Memory(pid_8476_luid_0x00000000_0x00011D4E_phys_0)\Local Usage";
        assert_eq!(
            key_of(path),
            "gpu_proc_mem.pid_8476_luid_0x00000000_0x00011D4E_phys_0.local_usage"
        );
    }

    #[test]
    fn the_spill_column_is_named_distinctly_from_the_resident_one() {
        // `Local` and `Non Local` differ by two characters in the counter path and mean opposite
        // things: resident VRAM versus the system memory a WDDM driver spilled into.
        let local = key_of(r"\\D\GPU Process Memory(pid_1)\Local Usage");
        let non_local = key_of(r"\\D\GPU Process Memory(pid_1)\Non Local Usage");
        assert_ne!(local, non_local);
        assert!(local.ends_with(".local_usage"));
        assert!(non_local.ends_with(".non_local_usage"));
    }

    #[test]
    fn typeperfs_trailing_chatter_is_not_a_sample() {
        let m = metrics_from_header(HEADER);
        assert!(parse_line(&m, "Exiting, please wait...", 0).is_none());
        assert!(parse_line(&m, "The command completed successfully.", 0).is_none());
        assert!(parse_line(&m, "", 0).is_none());
        assert!(parse_line(&m, HEADER, 0).is_none());
    }

    #[test]
    fn a_blank_counter_value_is_unsupported_not_zero() {
        // typeperf leaves a field empty when a counter momentarily has no instance. Read as 0 it
        // would drag a mean down and, worse, make a `min` of 0 look like a real trough.
        let m = metrics_from_header(HEADER);
        let row = "\"08/16/2026 10:36:10.260\",\"\",\"9983746048.000000\"";
        let s = parse_line(&m, row, 0).unwrap();
        assert_eq!(s.readings[0], Reading::NotSupported);
    }

    #[test]
    fn csv_fields_honours_quotes_and_doubled_quotes() {
        assert_eq!(csv_fields(r#""a","b""c""#), vec!["a", "b\"c"]);
        assert_eq!(csv_fields(r#""a,b","c""#), vec!["a,b", "c"]);
    }

    #[test]
    fn a_row_of_the_wrong_arity_is_dropped() {
        let m = metrics_from_header(HEADER);
        assert!(parse_line(&m, "\"08/16/2026 10:36:10.260\",\"1\"", 0).is_none());
    }

    #[test]
    fn a_counter_path_with_no_host_prefix_still_keys() {
        assert_eq!(key_of(r"\Memory\Available MBytes"), "mem.available_mbytes");
    }
}
