#[cfg(test)]
mod w8_hidden {
    use super::*;

    #[test]
    fn a_child_that_reads_stdin_sees_eof_rather_than_the_operators_keystrokes() {
        // Red only when the test binary has a live stdin: verify.sh pipes text into
        // `cargo test`. An unfixed child inherits it and reads that text back.
        let body = "import sys; sys.stdout.write(str(len(sys.stdin.read())))";
        let result = run_command_with_timeout("python", &["-c", body], 10, None);
        assert!(
            !(result.exit_code.is_none() && result.stderr.starts_with("failed to spawn")),
            "python is not on PATH, so this verifier cannot run: {result:?}"
        );
        assert!(!result.timed_out, "must see EOF at once: {result:?}");
        assert!(result.success, "child should exit 0: {result:?}");
        assert_eq!(result.stdout, "0", "must read nothing from stdin: {result:?}");
    }
}
