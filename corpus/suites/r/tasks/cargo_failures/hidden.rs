#[cfg(test)]
mod w8_hidden {
    use super::*;

    fn names(out: &str) -> Vec<String> {
        parse_cargo_failures(out)
            .iter()
            .map(|f| f["name"].as_str().unwrap_or("").to_string())
            .collect()
    }

    #[test]
    fn a_failure_in_short_output_is_reported() {
        let out = "---- a::b stdout ----\n\
                   thread 'a::b' panicked at src/x.rs:3:5:\n\
                   boom\n";
        assert_eq!(names(out), vec!["a::b".to_string()]);
    }

    #[test]
    fn a_failure_in_the_last_lines_of_long_output_is_reported() {
        let mut out = String::new();
        for i in 0..40 {
            out.push_str(&format!("test t{i} ... ok\n"));
        }
        out.push_str("\nfailures:\n\n---- tail::last stdout ----\n");
        out.push_str("thread 'tail::last' panicked at src/y.rs:9:1:\nnope\n");
        assert_eq!(names(&out), vec!["tail::last".to_string()]);
    }

    #[test]
    fn two_failures_are_each_reported_once() {
        let mut out = String::from("---- m::one stdout ----\n");
        out.push_str("thread 'm::one' panicked at src/a.rs:1:1:\nx\n\n");
        for i in 0..10 {
            out.push_str(&format!("note {i}\n"));
        }
        out.push_str("---- m::two stdout ----\nthread 'm::two' panicked at src/b.rs:2:2:\ny\n");
        assert_eq!(names(&out), vec!["m::one".to_string(), "m::two".to_string()]);
    }
}
