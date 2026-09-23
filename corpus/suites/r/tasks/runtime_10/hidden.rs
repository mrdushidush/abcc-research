#[cfg(test)]
mod w8_hidden {
    use super::*;

    #[test]
    fn rejects_deeply_nested_input_instead_of_recursing() {
        // 300 is well under any real stack limit for this parser, so an unfixed tree returns
        // Ok here rather than crashing: the test measures the missing limit, not a segfault.
        let depth = 300;
        let source = format!("{}{}", "[".repeat(depth), "]".repeat(depth));
        assert!(
            JsonValue::parse(&source).is_err(),
            "a {depth}-deep array parsed without hitting any nesting limit"
        );
    }

    #[test]
    fn rejects_deeply_nested_objects_too() {
        let depth = 300;
        let source = format!("{}null{}", "{\"a\":".repeat(depth), "}".repeat(depth));
        assert!(
            JsonValue::parse(&source).is_err(),
            "a {depth}-deep object parsed without hitting any nesting limit"
        );
    }

    #[test]
    fn shallow_nesting_still_parses() {
        let depth = 20;
        let source = format!("{}{}", "[".repeat(depth), "]".repeat(depth));
        assert!(JsonValue::parse(&source).is_ok(), "a {depth}-deep array must still parse");
    }
}
