//! What a sample is, and what an honest summary of a series of them may claim.
//!
//! The shape here exists to keep three distinctions that a naive `Vec<f64>` would lose, each of
//! which has already cost this project a wrong number somewhere:
//!
//! 1. **Unsupported is not zero.** `nvidia-smi` prints `[Not Supported]` for a field this card
//!    does not expose, and a parser that reads that as `0.0` reports a peak power draw of 0 W with
//!    a straight face. [`Reading`] mirrors `w8-run`'s `Metric` for the same reason SPEC §7 gives:
//!    `n/a` is where a real limitation has to stay visible, so it must never round to zero.
//! 2. **A peak over samples is a lower bound, not a peak.** Anything shorter than the gap between
//!    two samples is invisible. [`Cadence::max_gap_ms`] is therefore reported beside every peak —
//!    it is the width of the blind window, and it is the number that says how much the peak can be
//!    trusted. See the README's "what this instrument cannot see".
//! 3. **A bitmask has no mean.** `clocks_throttle_reasons.active` is flags; averaging it produces a
//!    number that looks like a measurement and means nothing. [`Agg::Bitmask`] aggregates by OR, so
//!    the question it answers is "did this ever throttle, and why", which is the question.

use std::collections::BTreeSet;
use std::fmt::Write as _;

// ---------------------------------------------------------------------------
// Metric definitions
// ---------------------------------------------------------------------------

/// How a metric's samples combine into one number.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Agg {
    /// min / max / mean / first / last are all meaningful.
    Numeric,
    /// Flags. Combined by OR; min, max and mean are refused rather than computed.
    Bitmask,
}

/// One column of a source's output, as declared in a static table.
///
/// `key` is what appears in the JSON; `query` is what the underlying tool is asked for. They differ
/// because the tool's spelling is the tool's business (`memory.used` is nvidia-smi's name for it)
/// and the output's spelling should survive a change of tool.
#[derive(Debug, Clone, Copy)]
pub struct MetricDef {
    pub key: &'static str,
    pub query: &'static str,
    pub unit: &'static str,
    pub agg: Agg,
}

/// One column of a *series*, after the columns are known.
///
/// Owned rather than `&'static str` because half the columns cannot be known at compile time:
/// `typeperf` expands a wildcard like `\GPU Process Memory(*)\Local Usage` into one column per
/// live process, and the instance names carry pids. A static table cannot name those, and the
/// alternative — leaking the strings to fake a `'static` — trades a real allocation for a fake
/// lifetime.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Metric {
    pub key: String,
    pub unit: String,
    pub agg: Agg,
}

impl From<&MetricDef> for Metric {
    fn from(d: &MetricDef) -> Metric {
        Metric {
            key: d.key.to_string(),
            unit: d.unit.to_string(),
            agg: d.agg,
        }
    }
}

impl Metric {
    pub fn new(key: impl Into<String>, unit: impl Into<String>, agg: Agg) -> Metric {
        Metric {
            key: key.into(),
            unit: unit.into(),
            agg,
        }
    }
}

// ---------------------------------------------------------------------------
// Readings
// ---------------------------------------------------------------------------

/// One cell of one sample.
#[derive(Debug, Clone, PartialEq)]
pub enum Reading {
    Measured(f64),
    /// The tool answered, and the answer was "this card/counter does not expose that".
    /// `nvidia-smi` spells it `[Not Supported]`; `typeperf` leaves the field blank.
    NotSupported,
    /// The tool answered `[N/A]` — the field exists but has no value in this context. Distinct
    /// from [`Reading::NotSupported`] because it is a property of the *moment*, not of the card:
    /// per-process VRAM reads `[N/A]` on this host's WDDM driver for every process, always.
    NotAvailable,
}

impl Reading {
    /// Parse one field of a tool's CSV output.
    ///
    /// Hex is accepted because `clocks_throttle_reasons.active` is a `0x…` bitmask, and it is
    /// carried as an `f64` like everything else: 64 bits of mask do not fit an `f64` mantissa
    /// exactly, but the flags actually defined occupy the low 9 bits, so the round trip is exact
    /// for every value the field can hold. [`Series::bits_seen`] re-widens it to `u64`.
    pub fn parse(raw: &str) -> Reading {
        let s = raw.trim();
        if s.eq_ignore_ascii_case("[not supported]") || s.is_empty() {
            return Reading::NotSupported;
        }
        if s.eq_ignore_ascii_case("[n/a]") || s.eq_ignore_ascii_case("[unknown error]") {
            return Reading::NotAvailable;
        }
        if let Some(hex) = s.strip_prefix("0x").or_else(|| s.strip_prefix("0X")) {
            return match u64::from_str_radix(hex, 16) {
                Ok(v) => Reading::Measured(v as f64),
                Err(_) => Reading::NotAvailable,
            };
        }
        match s.parse::<f64>() {
            Ok(v) => Reading::Measured(v),
            Err(_) => Reading::NotAvailable,
        }
    }

    pub fn value(&self) -> Option<f64> {
        match self {
            Reading::Measured(v) => Some(*v),
            _ => None,
        }
    }
}

// ---------------------------------------------------------------------------
// Samples
// ---------------------------------------------------------------------------

/// One row: every metric of one source, at one instant.
#[derive(Debug, Clone)]
pub struct Sample {
    /// Milliseconds since the probe started, taken from `Instant` when the line was **received**.
    ///
    /// Deliberately not the tool's own timestamp. The tool's clock says when the driver was
    /// queried; this one says when we could have noticed. Gaps in *this* series are the blind
    /// windows, so this is what [`Cadence`] is computed from. The tool's own stamp is kept beside
    /// it in [`Sample::device_ts`] and never silently substituted.
    pub t_ms: u64,
    /// The tool's own timestamp, verbatim, or empty when the tool emits none.
    pub device_ts: String,
    pub readings: Vec<Reading>,
}

// ---------------------------------------------------------------------------
// Cadence
// ---------------------------------------------------------------------------

/// How regularly the samples actually arrived.
///
/// Reported because the nominal interval is a request, not a measurement: `nvidia-smi -lms 100`
/// was observed delivering 104–115 ms on this host, and a scheduler hiccup or a busy GPU stretches
/// it further. A peak is only as good as the widest gap it survived.
#[derive(Debug, Clone, PartialEq)]
pub struct Cadence {
    pub n: usize,
    pub nominal_ms: u64,
    pub min_gap_ms: u64,
    pub max_gap_ms: u64,
    pub mean_gap_ms: f64,
    /// Total span from the first sample to the last.
    pub span_ms: u64,
}

impl Cadence {
    pub fn of(samples: &[Sample], nominal_ms: u64) -> Cadence {
        let mut min = u64::MAX;
        let mut max = 0u64;
        let mut total = 0u64;
        for w in samples.windows(2) {
            let gap = w[1].t_ms.saturating_sub(w[0].t_ms);
            min = min.min(gap);
            max = max.max(gap);
            total += gap;
        }
        let gaps = samples.len().saturating_sub(1);
        Cadence {
            n: samples.len(),
            nominal_ms,
            min_gap_ms: if gaps == 0 { 0 } else { min },
            max_gap_ms: max,
            mean_gap_ms: if gaps == 0 {
                0.0
            } else {
                total as f64 / gaps as f64
            },
            span_ms: match (samples.first(), samples.last()) {
                (Some(a), Some(b)) => b.t_ms.saturating_sub(a.t_ms),
                _ => 0,
            },
        }
    }

    fn to_json(&self) -> String {
        format!(
            "{{\"n\":{},\"nominal_ms\":{},\"min_gap_ms\":{},\"max_gap_ms\":{},\"mean_gap_ms\":{:.1},\"span_ms\":{}}}",
            self.n, self.nominal_ms, self.min_gap_ms, self.max_gap_ms, self.mean_gap_ms, self.span_ms
        )
    }
}

// ---------------------------------------------------------------------------
// Per-metric statistics
// ---------------------------------------------------------------------------

/// What a series of one metric supports being asked.
#[derive(Debug, Clone, PartialEq)]
pub enum Stats {
    /// At least one sample was a real number.
    Numeric {
        n: usize,
        min: f64,
        max: f64,
        mean: f64,
        first: f64,
        last: f64,
    },
    /// A bitmask: the OR of every sample, plus the individual bits that were ever set.
    Bits { n: usize, mask: u64 },
    /// Every sample was `[Not Supported]`. Reported as such, never as 0.
    NotSupported { n: usize },
    /// Every sample was `[N/A]`, or there were no samples at all.
    NotAvailable { n: usize },
}

impl Stats {
    pub fn max(&self) -> Option<f64> {
        match self {
            Stats::Numeric { max, .. } => Some(*max),
            _ => None,
        }
    }

    fn to_json(&self) -> String {
        match self {
            Stats::Numeric {
                n,
                min,
                max,
                mean,
                first,
                last,
            } => format!(
                "{{\"n\":{n},\"min\":{},\"max\":{},\"mean\":{:.2},\"first\":{},\"last\":{}}}",
                num(*min),
                num(*max),
                mean,
                num(*first),
                num(*last)
            ),
            Stats::Bits { n, mask } => {
                let names = throttle_reasons(*mask);
                let list = names
                    .iter()
                    .map(|s| format!("\"{s}\""))
                    .collect::<Vec<_>>()
                    .join(",");
                format!("{{\"n\":{n},\"mask\":\"0x{mask:016x}\",\"reasons\":[{list}]}}")
            }
            Stats::NotSupported { n } => format!("{{\"n\":{n},\"not_supported\":true}}"),
            Stats::NotAvailable { n } => format!("{{\"n\":{n},\"not_available\":true}}"),
        }
    }
}

/// Render a float without a trailing `.0` when it is integral, so a MiB reading is `585` and not
/// `585.0`. Cosmetic in JSON, but these files are read by hand as often as by a parser.
fn num(v: f64) -> String {
    if v.fract() == 0.0 && v.abs() < 9.0e15 {
        format!("{}", v as i64)
    } else {
        format!("{v}")
    }
}

/// Decode `clocks_throttle_reasons.active` into names.
///
/// The bit values are NVML's `nvmlClocksThrottleReason*` constants. `GpuIdle` is deliberately
/// included even though it fires constantly on an idle card: a decoder that hides a bit it thinks
/// is boring is a decoder you cannot trust when the bit you care about is the one it dropped. The
/// caller decides what is interesting — [`Summary::thermal_throttled`] is the narrow question.
pub fn throttle_reasons(mask: u64) -> Vec<&'static str> {
    const BITS: &[(u64, &str)] = &[
        (0x0000_0000_0000_0001, "GpuIdle"),
        (0x0000_0000_0000_0002, "ApplicationsClocksSetting"),
        (0x0000_0000_0000_0004, "SwPowerCap"),
        (0x0000_0000_0000_0008, "HwSlowdown"),
        (0x0000_0000_0000_0010, "SyncBoost"),
        (0x0000_0000_0000_0020, "SwThermalSlowdown"),
        (0x0000_0000_0000_0040, "HwThermalSlowdown"),
        (0x0000_0000_0000_0080, "HwPowerBrakeSlowdown"),
        (0x0000_0000_0000_0100, "DisplayClockSetting"),
    ];
    let mut out: Vec<&'static str> = BITS
        .iter()
        .filter(|(b, _)| mask & b != 0)
        .map(|(_, n)| *n)
        .collect();
    let known: u64 = BITS.iter().map(|(b, _)| b).sum();
    if mask & !known != 0 {
        out.push("Unknown");
    }
    out
}

/// The two bits that mean "this card slowed itself down because it was hot".
///
/// Separated from the full decode because it is the question two killed W8 campaigns actually
/// needed answered, and `GpuIdle` being set on every idle sample would otherwise drown it.
pub fn is_thermal(mask: u64) -> bool {
    mask & (0x20 | 0x40) != 0
}

// ---------------------------------------------------------------------------
// Series
// ---------------------------------------------------------------------------

/// Every sample from one source, plus the metric definitions they are rows of.
#[derive(Debug, Clone)]
pub struct Series {
    pub source: String,
    pub metrics: Vec<Metric>,
    pub samples: Vec<Sample>,
    pub nominal_ms: u64,
}

impl Series {
    pub fn new(source: impl Into<String>, metrics: Vec<Metric>, nominal_ms: u64) -> Series {
        Series {
            source: source.into(),
            metrics,
            samples: Vec::new(),
            nominal_ms,
        }
    }

    pub fn cadence(&self) -> Cadence {
        Cadence::of(&self.samples, self.nominal_ms)
    }

    /// Statistics for metric `i`.
    ///
    /// The three "no number" outcomes are kept apart on purpose. A metric with no samples at all
    /// and a metric the card refuses to report are different failures with different fixes, and
    /// collapsing them into one is how a probe comes to claim a card has no temperature sensor
    /// when in fact the probe never started.
    pub fn stats(&self, i: usize) -> Stats {
        let def = match self.metrics.get(i) {
            Some(d) => d,
            None => return Stats::NotAvailable { n: 0 },
        };
        let cells: Vec<&Reading> = self.samples.iter().filter_map(|s| s.readings.get(i)).collect();
        let n = cells.len();
        if def.agg == Agg::Bitmask {
            let mut mask = 0u64;
            let mut any = false;
            for c in &cells {
                if let Some(v) = c.value() {
                    mask |= v as u64;
                    any = true;
                }
            }
            return if any {
                Stats::Bits { n, mask }
            } else {
                Stats::NotSupported { n }
            };
        }
        let vals: Vec<f64> = cells.iter().filter_map(|c| c.value()).collect();
        if vals.is_empty() {
            // Which kind of nothing? If the card said "not supported" even once, that is the
            // durable answer; otherwise it is a transient absence.
            let unsupported = cells.iter().any(|c| **c == Reading::NotSupported);
            return if unsupported {
                Stats::NotSupported { n }
            } else {
                Stats::NotAvailable { n }
            };
        }
        let mut min = f64::INFINITY;
        let mut max = f64::NEG_INFINITY;
        let mut sum = 0.0;
        for v in &vals {
            min = min.min(*v);
            max = max.max(*v);
            sum += v;
        }
        Stats::Numeric {
            n: vals.len(),
            min,
            max,
            mean: sum / vals.len() as f64,
            first: vals[0],
            last: vals[vals.len() - 1],
        }
    }

    /// The OR of every bitmask sample of metric `key`, or 0 if there is no such metric.
    pub fn bits_seen(&self, key: &str) -> u64 {
        match self.index_of(key).map(|i| self.stats(i)) {
            Some(Stats::Bits { mask, .. }) => mask,
            _ => 0,
        }
    }

    pub fn index_of(&self, key: &str) -> Option<usize> {
        self.metrics.iter().position(|m| m.key == key)
    }

    /// Drop the columns `keep` rejects, from the metric list **and from every sample**.
    ///
    /// Used to prune `\Process(*)`'s 375 columns down to the one process a caller asked about.
    /// The two must move together: a metric list and a readings row that disagree on length is
    /// the mis-alignment that silently reports one counter's value under another's name, which is
    /// the same failure [`crate::gpu::parse_line`] refuses a short row to avoid.
    pub fn retain(&mut self, keep: impl Fn(&Metric) -> bool) {
        let mask: Vec<bool> = self.metrics.iter().map(&keep).collect();
        let mut i = 0;
        self.metrics.retain(|_| {
            let k = mask[i];
            i += 1;
            k
        });
        for s in &mut self.samples {
            let mut i = 0;
            s.readings.retain(|_| {
                let k = mask.get(i).copied().unwrap_or(false);
                i += 1;
                k
            });
        }
    }

    pub fn stats_of(&self, key: &str) -> Option<Stats> {
        self.index_of(key).map(|i| self.stats(i))
    }

    /// `key=value` rows for the human-readable summary, one metric per line.
    pub fn to_json(&self) -> String {
        let mut s = String::new();
        let _ = write!(
            s,
            "{{\"source\":{},\"cadence\":{},\"metrics\":{{",
            json_quote(&self.source),
            self.cadence().to_json()
        );
        for (i, m) in self.metrics.iter().enumerate() {
            if i > 0 {
                s.push(',');
            }
            let _ = write!(
                s,
                "{}:{{\"unit\":{},\"stats\":{}}}",
                json_quote(&m.key),
                json_quote(&m.unit),
                self.stats(i).to_json()
            );
        }
        s.push_str("}}");
        s
    }

    /// One JSON object per sample — the raw trace, for plotting or for re-reading a peak that the
    /// summary rounded. Written alongside the summary rather than instead of it, because a peak
    /// with no trace cannot be checked and a trace with no summary is not a result.
    pub fn to_jsonl(&self) -> String {
        let mut out = String::new();
        for s in &self.samples {
            let mut line = format!(
                "{{\"source\":{},\"t_ms\":{},\"device_ts\":{}",
                json_quote(&self.source),
                s.t_ms,
                json_quote(&s.device_ts)
            );
            for (i, m) in self.metrics.iter().enumerate() {
                match s.readings.get(i) {
                    Some(Reading::Measured(v)) => {
                        let _ = write!(line, ",{}:{}", json_quote(&m.key), num(*v));
                    }
                    Some(Reading::NotSupported) => {
                        let _ = write!(line, ",{}:\"not_supported\"", json_quote(&m.key));
                    }
                    Some(Reading::NotAvailable) | None => {
                        let _ = write!(line, ",{}:null", json_quote(&m.key));
                    }
                }
            }
            line.push('}');
            out.push_str(&line);
            out.push('\n');
        }
        out
    }
}

// ---------------------------------------------------------------------------
// JSON helpers
// ---------------------------------------------------------------------------

/// Quote a string as a JSON scalar. Hand-rolled for the same reason `w8-run` hand-rolls its own:
/// this crate has no third-party dependencies and adding one to emit six kinds of object is a bad
/// trade (see the workspace `Cargo.toml`).
pub fn json_quote(s: &str) -> String {
    let mut out = String::with_capacity(s.len() + 2);
    out.push('"');
    for c in s.chars() {
        match c {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            c if (c as u32) < 0x20 => {
                let _ = write!(out, "\\u{:04x}", c as u32);
            }
            c => out.push(c),
        }
    }
    out.push('"');
    out
}

/// The distinct instance names seen across a set of counter paths, in stable order.
pub fn distinct(names: impl IntoIterator<Item = String>) -> Vec<String> {
    names.into_iter().collect::<BTreeSet<_>>().into_iter().collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    fn defs() -> Vec<Metric> {
        vec![
            Metric::new("mem_used_mib", "MiB", Agg::Numeric),
            Metric::new("throttle", "bitmask", Agg::Bitmask),
        ]
    }

    fn sample(t: u64, mem: Reading, thr: Reading) -> Sample {
        Sample {
            t_ms: t,
            device_ts: String::new(),
            readings: vec![mem, thr],
        }
    }

    #[test]
    fn not_supported_never_reads_as_zero() {
        // The whole reason `Reading` exists. A card that does not report power draw must not be
        // summarised as drawing 0 W, which is what `unwrap_or(0.0)` would produce.
        let s = Series {
            source: "gpu".into(),
            metrics: defs(),
            samples: vec![
                sample(0, Reading::NotSupported, Reading::Measured(0.0)),
                sample(100, Reading::NotSupported, Reading::Measured(0.0)),
            ],
            nominal_ms: 100,
        };
        assert_eq!(s.stats(0), Stats::NotSupported { n: 2 });
        assert_eq!(s.stats(0).max(), None);
    }

    #[test]
    fn not_supported_and_not_available_do_not_collapse() {
        let unavailable = Series {
            source: "gpu".into(),
            metrics: defs(),
            samples: vec![sample(0, Reading::NotAvailable, Reading::NotAvailable)],
            nominal_ms: 100,
        };
        assert_eq!(unavailable.stats(0), Stats::NotAvailable { n: 1 });

        let empty = Series {
            source: "gpu".into(),
            metrics: defs(),
            samples: vec![],
            nominal_ms: 100,
        };
        // No samples is *also* NotAvailable — but with n=0, which is what tells the two apart.
        assert_eq!(empty.stats(0), Stats::NotAvailable { n: 0 });
    }

    #[test]
    fn a_bitmask_is_ored_and_never_averaged() {
        let s = Series {
            source: "gpu".into(),
            metrics: defs(),
            samples: vec![
                sample(0, Reading::Measured(1.0), Reading::Measured(0x01 as f64)),
                sample(100, Reading::Measured(2.0), Reading::Measured(0x20 as f64)),
                sample(200, Reading::Measured(3.0), Reading::Measured(0x01 as f64)),
            ],
            nominal_ms: 100,
        };
        // Mean of 0x1, 0x20, 0x1 would be 11.33 — a number that looks like a reading and is not
        // one. The OR is 0x21, which decodes to the two things that actually happened.
        assert_eq!(s.stats(1), Stats::Bits { n: 3, mask: 0x21 });
        assert_eq!(s.bits_seen("throttle"), 0x21);
        assert!(is_thermal(0x21));
        assert_eq!(
            throttle_reasons(0x21),
            vec!["GpuIdle", "SwThermalSlowdown"]
        );
    }

    #[test]
    fn an_idle_card_is_not_reported_as_thermally_throttled() {
        // `GpuIdle` (0x1) is set on essentially every sample of an idle card. If `is_thermal` were
        // "mask != 0" every quiet baseline would allege overheating.
        assert!(!is_thermal(0x1));
        assert!(is_thermal(0x40));
        assert!(!is_thermal(0x0));
    }

    #[test]
    fn an_unknown_throttle_bit_is_named_rather_than_dropped() {
        let r = throttle_reasons(0x8000_0000);
        assert_eq!(r, vec!["Unknown"]);
        assert_eq!(throttle_reasons(0x0), Vec::<&str>::new());
    }

    #[test]
    fn the_widest_gap_is_reported_because_it_is_the_blind_window() {
        // Samples at 0, 100, 900, 1000: the peak between 100 and 900 was never sampled, and
        // `max_gap_ms = 800` is the only thing in the output that admits it.
        let s = Series {
            source: "gpu".into(),
            metrics: defs(),
            samples: vec![
                sample(0, Reading::Measured(1.0), Reading::Measured(0.0)),
                sample(100, Reading::Measured(1.0), Reading::Measured(0.0)),
                sample(900, Reading::Measured(1.0), Reading::Measured(0.0)),
                sample(1000, Reading::Measured(1.0), Reading::Measured(0.0)),
            ],
            nominal_ms: 100,
        };
        let c = s.cadence();
        assert_eq!(c.max_gap_ms, 800);
        assert_eq!(c.min_gap_ms, 100);
        assert_eq!(c.span_ms, 1000);
        assert_eq!(c.n, 4);
        assert!((c.mean_gap_ms - 333.3).abs() < 0.1);
    }

    #[test]
    fn cadence_of_one_sample_claims_no_gaps() {
        let s = Series {
            source: "gpu".into(),
            metrics: defs(),
            samples: vec![sample(7, Reading::Measured(1.0), Reading::Measured(0.0))],
            nominal_ms: 100,
        };
        let c = s.cadence();
        // Not u64::MAX, which is what an unguarded `min` fold leaves behind.
        assert_eq!(c.min_gap_ms, 0);
        assert_eq!(c.max_gap_ms, 0);
        assert_eq!(c.span_ms, 0);
    }

    #[test]
    fn readings_parse_every_shape_nvidia_smi_emits() {
        assert_eq!(Reading::parse("585"), Reading::Measured(585.0));
        assert_eq!(Reading::parse(" 29.07 "), Reading::Measured(29.07));
        assert_eq!(
            Reading::parse("0x0000000000000021"),
            Reading::Measured(33.0)
        );
        assert_eq!(Reading::parse("[Not Supported]"), Reading::NotSupported);
        assert_eq!(Reading::parse("[N/A]"), Reading::NotAvailable);
        assert_eq!(Reading::parse(""), Reading::NotSupported);
        assert_eq!(Reading::parse("garbage"), Reading::NotAvailable);
    }

    #[test]
    fn a_full_bitmask_round_trips_through_f64() {
        // The only defined bits are the low 9, so the f64 carrier is exact for anything real.
        let mask = 0x1ffu64;
        let r = Reading::parse(&format!("0x{mask:016x}"));
        assert_eq!(r.value().map(|v| v as u64), Some(mask));
    }

    #[test]
    fn json_quote_escapes_what_a_windows_path_contains() {
        assert_eq!(json_quote(r"C:\x"), "\"C:\\\\x\"");
        assert_eq!(json_quote("a\"b"), "\"a\\\"b\"");
        assert_eq!(json_quote("a\nb"), "\"a\\nb\"");
    }

    #[test]
    fn jsonl_marks_unsupported_rather_than_omitting_the_key() {
        // A missing key reads as "the probe did not measure this"; the string says "the card does
        // not have it". Downstream that is the difference between re-running and not.
        let s = Series {
            source: "gpu".into(),
            metrics: defs(),
            samples: vec![sample(0, Reading::NotSupported, Reading::Measured(0.0))],
            nominal_ms: 100,
        };
        let l = s.to_jsonl();
        assert!(l.contains("\"mem_used_mib\":\"not_supported\""), "{l}");
        assert!(l.ends_with('\n'));
    }
}
