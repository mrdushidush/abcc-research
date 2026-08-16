//! The GPU source: one long-lived `nvidia-smi --query-gpu=… -lms N`, parsed line by line.
//!
//! **Why a streaming child rather than a shell-out per sample.** A single `nvidia-smi` invocation
//! costs **73–87 ms** on this host (measured, five runs). At the 100 ms cadence this probe wants,
//! per-sample spawning would burn most of a core and, worse, the spawn cost would land *inside*
//! the interval it is trying to measure. `-lms` keeps one process alive and streams CSV, which
//! costs one process for the whole run and delivers 104–115 ms actual against a 100 ms request.
//!
//! 🚨 **The streaming child does not die when its pipe closes.** Proved by accident here: a
//! `nvidia-smi … -lms 200 | head -3` left `nvidia-smi` running after `head` exited, and it had to
//! be killed by hand. On Windows there is no SIGPIPE to inherit. So [`GpuSource::stop`] kills the
//! **tree** explicitly — the same conclusion `w8-run`'s F57 fix reached from the other direction,
//! and for the same reason: a leaked child holding a pipe is not merely waste, it can hang the
//! process that spawned it.

use std::io::{BufRead, BufReader};
use std::process::{Child, Command, Stdio};
use std::sync::mpsc::{self, Receiver};
use std::thread::JoinHandle;
use std::time::{Duration, Instant};

use crate::sample::{Agg, Metric, MetricDef, Reading, Sample, Series};

/// What is asked of the card, in the order the CSV returns it.
///
/// `timestamp` is queried too but is not in this table: it is the device's own clock, kept beside
/// each sample as [`Sample::device_ts`] rather than aggregated. `memory.reserved` is here because
/// the driver's own reservation (261 MiB on this card) is part of what the 16,311 MiB is spent on,
/// and a residency budget that ignores it over-promises by a sixth of a gigabyte.
pub const GPU_METRICS: &[MetricDef] = &[
    MetricDef {
        key: "mem_used_mib",
        query: "memory.used",
        unit: "MiB",
        agg: Agg::Numeric,
    },
    MetricDef {
        key: "mem_reserved_mib",
        query: "memory.reserved",
        unit: "MiB",
        agg: Agg::Numeric,
    },
    MetricDef {
        key: "mem_total_mib",
        query: "memory.total",
        unit: "MiB",
        agg: Agg::Numeric,
    },
    MetricDef {
        key: "temp_c",
        query: "temperature.gpu",
        unit: "C",
        agg: Agg::Numeric,
    },
    MetricDef {
        key: "util_gpu_pct",
        query: "utilization.gpu",
        unit: "%",
        agg: Agg::Numeric,
    },
    MetricDef {
        key: "util_mem_pct",
        query: "utilization.memory",
        unit: "%",
        agg: Agg::Numeric,
    },
    MetricDef {
        key: "power_w",
        query: "power.draw",
        unit: "W",
        agg: Agg::Numeric,
    },
    MetricDef {
        key: "clocks_sm_mhz",
        query: "clocks.sm",
        unit: "MHz",
        agg: Agg::Numeric,
    },
    MetricDef {
        key: "throttle",
        query: "clocks_throttle_reasons.active",
        unit: "bitmask",
        agg: Agg::Bitmask,
    },
];

/// Split one CSV row into fields.
///
/// `--format=csv,noheader,nounits` emits `, `-separated plain values with no quoting and no
/// embedded commas — a timestamp is `2026/08/16 10:39:09.628`, spaces and all. So a naive split on
/// `,` plus a trim is correct here, and a full CSV reader would be ceremony.
fn fields(line: &str) -> Vec<&str> {
    line.split(',').map(str::trim).collect()
}

/// Turn one streamed line into a sample, or `None` if it is not a data row.
///
/// Non-data lines are real: `nvidia-smi` writes warnings to the same stream in some driver
/// versions, and a row with the wrong arity means the query and the parser have drifted apart.
/// Both are dropped rather than guessed at, because a mis-aligned row would silently assign the
/// temperature column's number to power draw.
pub fn parse_line(metrics: &[MetricDef], line: &str, t_ms: u64) -> Option<Sample> {
    let f = fields(line);
    if f.len() != metrics.len() + 1 {
        return None;
    }
    // Column 0 is the timestamp. If it does not look like one, this is not a data row.
    let ts = f[0];
    if ts.is_empty() || !ts.starts_with(|c: char| c.is_ascii_digit()) {
        return None;
    }
    Some(Sample {
        t_ms,
        device_ts: ts.to_string(),
        readings: f[1..].iter().map(|c| Reading::parse(c)).collect(),
    })
}

/// Ask `nvidia-smi` once for every metric in `want`, and return the subset it accepts.
///
/// A field this driver does not know is a **hard** error — `nvidia-smi` exits 2 with
/// `Field "x" is not a valid field to query.` and prints no data at all — so one bad name would
/// cost every other metric. Rather than pinning the table to this card, the fallback re-probes
/// field by field and drops the ones that are refused. That is what makes the crate portable to
/// the "if you only have 8GB" and "24GB or more" boxes W1's deliverable has to speak to.
pub fn supported_metrics(want: &[MetricDef]) -> Result<Vec<MetricDef>, String> {
    if want.is_empty() {
        return Ok(Vec::new());
    }
    if one_shot(want).is_ok() {
        return Ok(want.to_vec());
    }
    let mut ok = Vec::new();
    for m in want {
        if one_shot(std::slice::from_ref(m)).is_ok() {
            ok.push(*m);
        }
    }
    if ok.is_empty() {
        Err("nvidia-smi accepted none of the requested fields".to_string())
    } else {
        Ok(ok)
    }
}

fn one_shot(metrics: &[MetricDef]) -> Result<String, String> {
    let query = metrics
        .iter()
        .map(|m| m.query)
        .collect::<Vec<_>>()
        .join(",");
    let out = Command::new("nvidia-smi")
        .arg(format!("--query-gpu={query}"))
        .arg("--format=csv,noheader,nounits")
        .stdin(Stdio::null())
        .output()
        .map_err(|e| format!("nvidia-smi did not run: {e}"))?;
    if !out.status.success() {
        let msg = String::from_utf8_lossy(&out.stdout);
        let err = String::from_utf8_lossy(&out.stderr);
        return Err(format!("{}{}", msg.trim(), err.trim()));
    }
    Ok(String::from_utf8_lossy(&out.stdout).trim().to_string())
}

/// A running `nvidia-smi` stream.
pub struct GpuSource {
    child: Child,
    reader: Option<JoinHandle<()>>,
    rx: Receiver<(u64, String)>,
    metrics: Vec<MetricDef>,
    nominal_ms: u64,
    t0: Instant,
    /// The sample [`GpuSource::warm_up`] consumed to prove the stream is alive. Kept rather than
    /// discarded — it is a real reading of the moment the probe started, which for a `run` is the
    /// pre-workload baseline.
    pending: Vec<Sample>,
}

impl GpuSource {
    /// Spawn the stream. `metrics` should already have been through [`supported_metrics`].
    pub fn start(interval_ms: u64, metrics: Vec<MetricDef>) -> Result<GpuSource, String> {
        let query = std::iter::once("timestamp".to_string())
            .chain(metrics.iter().map(|m| m.query.to_string()))
            .collect::<Vec<_>>()
            .join(",");
        // `-lms` and its value must be separate arguments. `-lms100` is rejected outright with
        // `ERROR: Option -lms100 is not recognized` — printed to **stdout**, after which the
        // process exits 0. Silence with a success code is precisely the failure shape this repo
        // keeps paying for (F49, F57), which is why the warm-up below refuses to return a source
        // that has not actually produced a sample.
        let mut child = Command::new("nvidia-smi")
            .arg(format!("--query-gpu={query}"))
            .arg("--format=csv,noheader,nounits")
            .arg("-lms")
            .arg(interval_ms.to_string())
            .stdin(Stdio::null())
            .stdout(Stdio::piped())
            .stderr(Stdio::null())
            .spawn()
            .map_err(|e| format!("could not start nvidia-smi: {e}"))?;
        let stdout = child
            .stdout
            .take()
            .ok_or_else(|| "nvidia-smi gave no stdout".to_string())?;
        let t0 = Instant::now();
        let (tx, rx) = mpsc::channel();
        // The reader thread does no parsing: it stamps arrival and hands the line on. Parsing on
        // this thread would put `Reading::parse` between the read and the next line's arrival,
        // which is small but is exactly the kind of cost that biases a cadence measurement.
        let reader = std::thread::spawn(move || {
            for line in BufReader::new(stdout).lines().map_while(Result::ok) {
                if tx.send((t0.elapsed().as_millis() as u64, line)).is_err() {
                    break;
                }
            }
        });
        let mut src = GpuSource {
            child,
            reader: Some(reader),
            rx,
            metrics,
            nominal_ms: interval_ms,
            t0,
            pending: Vec::new(),
        };
        src.warm_up(interval_ms)?;
        Ok(src)
    }

    /// Block until the stream produces one real sample, or give up and say why.
    ///
    /// Without this, a source that starts and immediately dies returns `Ok` and then reports zero
    /// samples at the end of the run — a measurement that silently did not happen. That is how the
    /// `-lms100` typo above survived a clean build, a clean clippy and 37 passing tests, and only
    /// showed up as `n/a` in a live baseline. Any non-sample text the tool emitted is quoted back,
    /// because `nvidia-smi` puts its usage errors on stdout and they are the whole diagnosis.
    fn warm_up(&mut self, interval_ms: u64) -> Result<(), String> {
        let grace = Duration::from_millis((interval_ms * 4).clamp(1_500, 10_000));
        let deadline = Instant::now() + grace;
        let mut chatter: Vec<String> = Vec::new();
        while Instant::now() < deadline {
            let left = deadline.saturating_duration_since(Instant::now());
            match self.rx.recv_timeout(left) {
                Ok((t, line)) => match parse_line(&self.metrics, &line, t) {
                    Some(s) => {
                        self.pending.push(s);
                        return Ok(());
                    }
                    None if !line.trim().is_empty() => chatter.push(line),
                    None => {}
                },
                Err(_) => break,
            }
        }
        crate::kill_tree(&mut self.child);
        if let Some(h) = self.reader.take() {
            let _ = h.join();
        }
        let why = if chatter.is_empty() {
            format!("no sample within {} ms and it said nothing", grace.as_millis())
        } else {
            chatter.join(" / ")
        };
        Err(format!("nvidia-smi produced no usable sample: {why}"))
    }

    /// Milliseconds since the stream started.
    pub fn elapsed_ms(&self) -> u64 {
        self.t0.elapsed().as_millis() as u64
    }

    /// Everything received so far, without stopping. Cheap; safe to call in a poll loop.
    pub fn drain(&self, into: &mut Vec<Sample>) {
        while let Ok((t, line)) = self.rx.try_recv() {
            if let Some(s) = parse_line(&self.metrics, &line, t) {
                into.push(s);
            }
        }
    }

    /// Kill the stream and return everything it produced.
    pub fn stop(mut self) -> Series {
        let mut samples = std::mem::take(&mut self.pending);
        self.drain(&mut samples);
        crate::kill_tree(&mut self.child);
        // The reader ends when the pipe closes, which the kill guarantees. Draining after the
        // join rather than before it is what stops the last sample or two from being lost.
        if let Some(h) = self.reader.take() {
            let _ = h.join();
        }
        while let Ok((t, line)) = self.rx.try_recv() {
            if let Some(s) = parse_line(&self.metrics, &line, t) {
                samples.push(s);
            }
        }
        Series {
            source: "gpu".to_string(),
            metrics: self.metrics.iter().map(Metric::from).collect(),
            samples,
            nominal_ms: self.nominal_ms,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    /// The exact bytes this host's `nvidia-smi` streamed, captured 2026-08-16. Kept verbatim so
    /// the parser is tested against the real format rather than against a format I remembered.
    const REAL: &str = "2026/08/16 10:39:09.628, 585, 261, 16311, 52, 2, 0, 29.07, 2820, 0x0000000000000000";

    #[test]
    fn the_real_captured_line_parses_into_every_column() {
        let s = parse_line(GPU_METRICS, REAL, 42).expect("real line must parse");
        assert_eq!(s.t_ms, 42);
        assert_eq!(s.device_ts, "2026/08/16 10:39:09.628");
        assert_eq!(s.readings.len(), GPU_METRICS.len());
        assert_eq!(s.readings[0], Reading::Measured(585.0)); // mem_used_mib
        assert_eq!(s.readings[1], Reading::Measured(261.0)); // mem_reserved_mib
        assert_eq!(s.readings[2], Reading::Measured(16311.0)); // mem_total_mib
        assert_eq!(s.readings[3], Reading::Measured(52.0)); // temp_c
        assert_eq!(s.readings[8], Reading::Measured(0.0)); // throttle
    }

    #[test]
    fn a_row_of_the_wrong_arity_is_dropped_not_shifted() {
        // The failure this guards is silent and severe: one missing column slides every reading
        // one place left, so power draw is reported as the memory-utilisation percentage.
        let short = "2026/08/16 10:39:09.628, 585, 261, 16311";
        assert!(parse_line(GPU_METRICS, short, 0).is_none());
        let long = format!("{REAL}, 99");
        assert!(parse_line(GPU_METRICS, &long, 0).is_none());
    }

    #[test]
    fn a_warning_line_is_not_a_sample() {
        assert!(parse_line(GPU_METRICS, "", 0).is_none());
        assert!(
            parse_line(
                GPU_METRICS,
                "Unable to determine the device handle for GPU 0000:01:00.0",
                0
            )
            .is_none()
        );
    }

    #[test]
    fn an_unsupported_field_survives_as_unsupported() {
        // A card without a power sensor: the row still parses, and the column stays `[Not
        // Supported]` rather than becoming 0 W.
        let line = "2026/08/16 10:39:09.628, 585, 261, 16311, 52, 2, 0, [Not Supported], 2820, 0x0";
        let s = parse_line(GPU_METRICS, line, 0).expect("must still parse");
        assert_eq!(s.readings[6], Reading::NotSupported);
        assert_eq!(s.readings[7], Reading::Measured(2820.0));
    }

    #[test]
    fn fields_keeps_the_spaces_inside_a_timestamp() {
        let f = fields(REAL);
        assert_eq!(f[0], "2026/08/16 10:39:09.628");
        assert_eq!(f.len(), GPU_METRICS.len() + 1);
    }

    #[test]
    fn an_empty_metric_list_needs_no_gpu() {
        assert_eq!(supported_metrics(&[]).unwrap().len(), 0);
    }
}
