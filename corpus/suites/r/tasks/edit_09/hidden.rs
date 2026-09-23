#[cfg(test)]
mod w8_hidden {
    use super::*;

    fn apply_one(diff: &str, original: &str) -> String {
        let files = parse_diff(diff).expect("the diff parses");
        assert_eq!(files.len(), 1, "one file expected, got {}", files.len());
        apply_hunks(original, &files[0].hunks).expect("the hunks apply").0
    }

    #[test]
    fn an_added_line_that_starts_with_two_pluses_is_kept() {
        let diff = "--- a/f.txt\n+++ b/f.txt\n@@ -1,2 +1,3 @@\n a\n+++ added\n b\n";
        assert_eq!(apply_one(diff, "a\nb\n"), "a\n++ added\nb\n");
    }

    #[test]
    fn a_deleted_signature_delimiter_is_deleted() {
        let diff = "--- a/m.txt\n+++ b/m.txt\n@@ -1,3 +1,2 @@\n body\n--- \n end\n";
        assert_eq!(apply_one(diff, "body\n-- \nend\n"), "body\nend\n");
    }

    #[test]
    fn a_second_file_header_after_a_finished_hunk_is_still_a_header() {
        let diff = "--- a/x.txt\n+++ b/x.txt\n@@ -1 +1 @@\n-old\n+new\n\
                    --- a/y.txt\n+++ b/y.txt\n@@ -1 +1 @@\n-one\n+two\n";
        let files = parse_diff(diff).expect("the diff parses");
        let paths: Vec<&str> = files.iter().map(|f| f.path.as_str()).collect();
        assert_eq!(paths, vec!["x.txt", "y.txt"]);
        assert_eq!(apply_hunks("old\n", &files[0].hunks).unwrap().0, "new\n");
        assert_eq!(apply_hunks("one\n", &files[1].hunks).unwrap().0, "two\n");
    }
}
