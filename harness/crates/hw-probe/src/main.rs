//! `hw-probe` — the CLI.
//!
//! Three verbs, and the third is the one that gets used:
//!
//! ```text
//! hw-probe doctor                      what is available on this box, and what is not
//! hw-probe watch --for 60s             sample for a fixed window
//! hw-probe run -- lms load qwen…       sample for exactly as long as a command runs
//! ```
//!
//! `run` exits with the wrapped command's own status, so it can be dropped in front of an existing
//! step without changing what the step means to whatever called it.

use std::io::Write as _;
use std::path::PathBuf;
use std::process::{Command, Stdio};
use std::time::Duration;

use hw_probe::{Config, Probe, Report, gpu, host};

const POLL: Duration = Duration::from_millis(200);

fn main() {
    let args: Vec<String> = std::env::args().skip(1).collect();
    if args.is_empty() || args[0] == "-h" || args[0] == "--help" {
        print!("{USAGE}");
        return;
    }
    let code = match args[0].as_str() {
        "doctor" => doctor(),
        "watch" => watch(&args[1..]),
        "run" => run(&args[1..]),
        "baseline" => baseline(&args[1..]),
        other => {
            eprintln!("hw-probe: unknown verb `{other}`\n");
            print!("{USAGE}");
            2
        }
    };
    std::process::exit(code);
}

const USAGE: &str = "\
hw-probe — peak VRAM, peak system RAM, temperature and throttle, around any workload

USAGE
  hw-probe doctor
  hw-probe watch  [--for <dur>] [options]
  hw-probe run    [options] -- <command> [args...]
  hw-probe baseline [--for <dur>] [options]

VERBS
  doctor     Report which sources this box supports, and what each cannot see.
  watch      Sample for a fixed window. Ctrl-C also stops it and still writes the report.
  run        Sample for exactly as long as <command> runs. Exits with the command's status.
  baseline   A `watch` labelled `baseline`, for the with-nothing-loaded reading that every
             VRAM delta on this host has to be measured against — `nvidia-smi` cannot
             attribute VRAM per process here, so subtraction is the only attribution.

OPTIONS
  --for <dur>          Window for watch/baseline. `30s`, `2m`, `500ms`. Default 30s.
  --gpu-interval <ms>  GPU sample interval. Default 100.
  --host-interval <s>  Host sample interval, in whole seconds. Default 1. `typeperf`'s own
                       floor is 1 second and values below it are clamped, not rejected.
  --per-process        Add Windows' per-process GPU memory counters, including the Non Local
                       (spill) column. Off by default: the wildcard adds ~25 columns.
                       Wildcards are resolved when the probe starts, so a process that
                       appears later gets no column — start the probe after your target.
  --pid <n>            Attribute residency to one process. Implies --per-process. WITHOUT
                       THIS NO RESIDENCY CLAIM IS MADE: ordinary desktop processes hold
                       shared GPU memory constantly (15.9 MiB on an idle baseline here), so
                       a system-wide Non Local total cannot tell a spilling model from
                       Explorer. For LM Studio this is the server process that holds the
                       weights, which already exists before `lms load` runs.
  --no-gpu, --no-host  Turn a source off.
  --label <text>       Carried into the report.
  --out <path>         Write the report JSON here, and the raw trace beside it as
                       <path>.jsonl. Without it, the summary goes to stdout only.
  --quiet              Suppress the human-readable summary.
";

fn parse_dur(s: &str) -> Option<Duration> {
    let s = s.trim();
    let (num, mult) = if let Some(n) = s.strip_suffix("ms") {
        (n, 1.0)
    } else if let Some(n) = s.strip_suffix('s') {
        (n, 1000.0)
    } else if let Some(n) = s.strip_suffix('m') {
        (n, 60_000.0)
    } else {
        (s, 1000.0)
    };
    num.parse::<f64>()
        .ok()
        .map(|v| Duration::from_millis((v * mult) as u64))
}

struct Opts {
    config: Config,
    window: Duration,
    out: Option<PathBuf>,
    quiet: bool,
    rest: Vec<String>,
}

/// Parse the options, stopping at `--`. Anything after `--` is the wrapped command and is not
/// interpreted — otherwise a probe of `lms load … --gpu max` would eat the subject's own flags.
fn opts(args: &[String]) -> Result<Opts, String> {
    let mut o = Opts {
        config: Config::default(),
        window: Duration::from_secs(30),
        out: None,
        quiet: false,
        rest: Vec::new(),
    };
    let mut i = 0;
    while i < args.len() {
        let a = args[i].as_str();
        let val = |i: &mut usize| -> Result<String, String> {
            *i += 1;
            args.get(*i)
                .cloned()
                .ok_or_else(|| format!("{a} needs a value"))
        };
        match a {
            "--" => {
                o.rest = args[i + 1..].to_vec();
                return Ok(o);
            }
            "--for" => {
                let v = val(&mut i)?;
                o.window = parse_dur(&v).ok_or_else(|| format!("bad duration `{v}`"))?;
            }
            "--gpu-interval" => {
                let v = val(&mut i)?;
                o.config.gpu_interval_ms =
                    v.parse().map_err(|_| format!("bad interval `{v}`"))?;
            }
            "--host-interval" => {
                let v = val(&mut i)?;
                o.config.host_interval_s =
                    v.parse().map_err(|_| format!("bad interval `{v}`"))?;
            }
            "--label" => o.config.label = val(&mut i)?,
            "--out" => o.out = Some(PathBuf::from(val(&mut i)?)),
            "--per-process" => o.config.per_process = true,
            "--pid" => {
                let v = val(&mut i)?;
                o.config.focus_pid = Some(v.parse().map_err(|_| format!("bad pid `{v}`"))?);
            }
            "--no-gpu" => o.config.gpu = false,
            "--no-host" => o.config.host = false,
            "--quiet" => o.quiet = true,
            other => return Err(format!("unknown option `{other}`")),
        }
        i += 1;
    }
    Ok(o)
}

fn doctor() -> i32 {
    println!("hw-probe doctor");
    match gpu::supported_metrics(gpu::GPU_METRICS) {
        Ok(m) => {
            println!("  nvidia-smi     OK — {} of {} fields", m.len(), gpu::GPU_METRICS.len());
            let missing: Vec<&str> = gpu::GPU_METRICS
                .iter()
                .filter(|d| !m.iter().any(|k| k.key == d.key))
                .map(|d| d.query)
                .collect();
            if !missing.is_empty() {
                println!("                 refused: {}", missing.join(", "));
            }
        }
        Err(e) => println!("  nvidia-smi     UNAVAILABLE — {e}"),
    }
    // The host source proves itself by producing a header, which is also the moment its wildcard
    // set is fixed. A shorter check would only prove the binary exists.
    let counters: Vec<String> = host::HOST_COUNTERS
        .iter()
        .map(|(p, _, _)| p.to_string())
        .collect();
    match host::HostSource::start(1, &counters) {
        Ok(mut h) => {
            let deadline = std::time::Instant::now() + Duration::from_secs(4);
            while h.metrics().is_empty() && std::time::Instant::now() < deadline {
                std::thread::sleep(POLL);
                h.drain();
            }
            let n = h.metrics().len();
            let s = h.stop();
            if n == 0 {
                println!("  typeperf       STARTED but produced no header within 4s");
            } else {
                println!(
                    "  typeperf       OK — {n} counters, header in {} ms, {} sample(s) taken",
                    s.cadence().span_ms.max(1),
                    s.samples.len()
                );
            }
        }
        Err(e) => println!("  typeperf       UNAVAILABLE — {e}"),
    }
    println!("\n  what this box cannot do:");
    println!("    - per-process VRAM from nvidia-smi: --query-compute-apps returns [N/A] on a");
    println!("      consumer WDDM driver. Use --per-process (Windows counters) or subtract a");
    println!("      `hw-probe baseline`.");
    println!("    - host sampling faster than 1 s: typeperf's -si floor.");
    println!("    - a true peak: every number here is a maximum over samples, and the report's");
    println!("      blind window says how wide the gap between them ever got.");
    0
}

fn finish(report: Report, o: &Opts) -> i32 {
    if !o.quiet {
        print!("{}", report.render());
    }
    if let Some(p) = &o.out {
        // LF, deliberately. Everything tracked in this repo is LF in the index and this file is
        // meant to be committable as evidence; letting a Windows default make it CRLF is the
        // mistake this project has paid for seven times.
        let json = format!("{}\n", report.to_json());
        if let Err(e) = std::fs::write(p, json.as_bytes()) {
            eprintln!("hw-probe: could not write {}: {e}", p.display());
            return 1;
        }
        // `report.json` → `report.jsonl`; anything else simply gains the suffix. The trace sits
        // beside the summary rather than replacing it: a peak with no trace cannot be checked,
        // and a trace with no summary is not a result.
        let trace = if p.extension().is_some_and(|e| e == "json") {
            p.with_extension("jsonl")
        } else {
            let mut t = p.clone().into_os_string();
            t.push(".jsonl");
            PathBuf::from(t)
        };
        let mut body = String::new();
        if let Some(g) = &report.gpu {
            body.push_str(&g.to_jsonl());
        }
        if let Some(h) = &report.host {
            body.push_str(&h.to_jsonl());
        }
        if let Err(e) = std::fs::write(&trace, body.as_bytes()) {
            eprintln!("hw-probe: could not write {}: {e}", trace.display());
            return 1;
        }
        if !o.quiet {
            println!("  wrote {} and {}", p.display(), trace.display());
        }
    }
    report.child_status.unwrap_or(0)
}

fn watch(args: &[String]) -> i32 {
    let o = match opts(args) {
        Ok(o) => o,
        Err(e) => {
            eprintln!("hw-probe: {e}");
            return 2;
        }
    };
    let mut p = Probe::start(o.config.clone());
    let deadline = std::time::Instant::now() + o.window;
    while std::time::Instant::now() < deadline {
        std::thread::sleep(POLL);
        p.poll();
    }
    finish(p.stop(), &o)
}

fn baseline(args: &[String]) -> i32 {
    let mut args = args.to_vec();
    if !args.iter().any(|a| a == "--label") {
        args.push("--label".into());
        args.push("baseline".into());
    }
    watch(&args)
}

fn run(args: &[String]) -> i32 {
    let o = match opts(args) {
        Ok(o) => o,
        Err(e) => {
            eprintln!("hw-probe: {e}");
            return 2;
        }
    };
    if o.rest.is_empty() {
        eprintln!("hw-probe: `run` needs a command after `--`");
        return 2;
    }
    let mut p = Probe::start(o.config.clone());
    p.note(format!("command: {}", o.rest.join(" ")));
    // Inherit stdio: the wrapped command's own output is the reason someone is running it, and
    // capturing it would change its behaviour (a progress bar that sees a pipe prints differently).
    let child = Command::new(&o.rest[0])
        .args(&o.rest[1..])
        .stdin(Stdio::inherit())
        .stdout(Stdio::inherit())
        .stderr(Stdio::inherit())
        .spawn();
    let mut child = match child {
        Ok(c) => c,
        Err(e) => {
            eprintln!("hw-probe: could not start `{}`: {e}", o.rest[0]);
            let _ = p.stop();
            return 2;
        }
    };
    let status = loop {
        match child.try_wait() {
            Ok(Some(s)) => break s.code().unwrap_or(-1),
            Ok(None) => {
                std::thread::sleep(POLL);
                p.poll();
            }
            Err(e) => {
                eprintln!("hw-probe: lost track of the child: {e}");
                break -1;
            }
        }
    };
    // One last poll so the samples taken during the command's final moments are not dropped.
    p.poll();
    let mut report = p.stop();
    report.child_status = Some(status);
    let _ = std::io::stdout().flush();
    finish(report, &o)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn durations_accept_the_three_suffixes_and_default_to_seconds() {
        assert_eq!(parse_dur("500ms"), Some(Duration::from_millis(500)));
        assert_eq!(parse_dur("30s"), Some(Duration::from_secs(30)));
        assert_eq!(parse_dur("2m"), Some(Duration::from_secs(120)));
        assert_eq!(parse_dur("45"), Some(Duration::from_secs(45)));
        assert_eq!(parse_dur("1.5s"), Some(Duration::from_millis(1500)));
        assert_eq!(parse_dur("soon"), None);
    }

    #[test]
    fn everything_after_the_separator_belongs_to_the_wrapped_command() {
        // The failure this prevents: `hw-probe run -- lms load m --gpu max` parsing `--gpu` as
        // its own flag and then complaining, or worse, silently consuming it.
        let args: Vec<String> = ["--label", "x", "--", "lms", "load", "m", "--gpu", "max"]
            .iter()
            .map(|s| s.to_string())
            .collect();
        let o = opts(&args).unwrap();
        assert_eq!(o.config.label, "x");
        assert_eq!(o.rest, vec!["lms", "load", "m", "--gpu", "max"]);
    }

    #[test]
    fn an_unknown_option_is_refused_rather_than_ignored() {
        let args: Vec<String> = vec!["--nope".to_string()];
        assert!(opts(&args).is_err());
    }

    #[test]
    fn a_missing_option_value_is_refused() {
        let args: Vec<String> = vec!["--label".to_string()];
        assert!(opts(&args).is_err());
    }

    #[test]
    fn defaults_match_what_the_two_tools_can_actually_deliver() {
        let o = opts(&[]).unwrap();
        assert_eq!(o.config.gpu_interval_ms, 100);
        assert_eq!(o.config.host_interval_s, 1);
        assert!(!o.config.per_process);
        assert!(o.config.gpu && o.config.host);
    }
}
