#[cfg(test)]
mod w8_hidden {
    use super::*;

    #[test]
    fn a_tool_that_exits_non_zero_reports_no_version() {
        // cargo is on PATH in every test run; an unknown flag makes it print an
        // error and exit non-zero — the same shape as a broken rustup shim.
        let got = command_first_line("cargo", "--w8-no-such-flag");
        assert_eq!(got, None, "an error line was reported as the version");
    }

    #[test]
    fn a_working_tool_still_reports_its_version() {
        let v = command_first_line("cargo", "--version").expect("cargo --version runs");
        assert!(v.starts_with("cargo "), "got {v}");
    }

    #[test]
    fn a_missing_tool_still_reports_none() {
        assert_eq!(command_first_line("w8-no-such-binary-xyz", "--version"), None);
    }
}
