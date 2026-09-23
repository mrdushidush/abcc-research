#[cfg(test)]
mod w8_hidden {
    use super::*;
    use std::time::{Duration, Instant};

    /// A child that spawns a grandchild which inherits the pipes and outlives it.
    const SPAWNS_A_SURVIVING_GRANDCHILD: &str = concat!(
        "import subprocess, sys, time\n",
        "subprocess.Popen(\n",
        "    [sys.executable, '-c', 'import time; time.sleep(60)'],\n",
        "    stdout=sys.stdout, stderr=sys.stderr, close_fds=False,\n",
        ")\n",
        "time.sleep(60)\n",
    );

    #[test]
    fn timeout_returns_promptly_when_a_grandchild_holds_the_pipes() {
        let probe = run_command_with_timeout("python", &["-c", "pass"], 10, None);
        assert!(probe.success, "python is not runnable, so this verifier cannot run: {probe:?}");

        let started = Instant::now();
        let result =
            run_command_with_timeout("python", &["-c", SPAWNS_A_SURVIVING_GRANDCHILD], 3, None);
        let elapsed = started.elapsed();

        assert!(result.timed_out, "the 3 s budget should have fired: {result:?}");
        assert!(
            elapsed < Duration::from_secs(25),
            "returned after {elapsed:?}, far past the 3 s budget"
        );
    }
}
