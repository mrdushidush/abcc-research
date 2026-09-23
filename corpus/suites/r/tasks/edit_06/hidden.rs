#[cfg(test)]
mod w8_hidden {
    use super::*;

    fn one_line_edit(original: &str, from: &str, to: &str, at: usize) -> String {
        let hunk = Hunk {
            old_start: at,
            old_lines: vec![from.to_string()],
            new_lines: vec![to.to_string()],
        };
        apply_hunks(original, &[hunk]).expect("the hunk applies").0
    }

    #[test]
    fn lines_outside_the_hunk_keep_their_own_line_endings() {
        let out = one_line_edit("a\r\nb\nc\n", "b", "B", 2);
        assert!(out.starts_with("a\r\n"), "line a changed: {out:?}");
        assert!(out.ends_with("\nc\n") && !out.ends_with("c\r\n"), "line c changed: {out:?}");
        assert!(out == "a\r\nB\nc\n" || out == "a\r\nB\r\nc\n", "got {out:?}");
    }

    #[test]
    fn a_crlf_line_among_lf_lines_is_not_converted() {
        let out = one_line_edit("x\ny\r\nz\n", "x", "X", 1);
        assert_eq!(&out[out.len() - "y\r\nz\n".len()..], "y\r\nz\n", "got {out:?}");
    }

    #[test]
    fn uniform_files_keep_their_style() {
        assert_eq!(one_line_edit("a\nb\nc\n", "b", "B", 2), "a\nB\nc\n");
        assert_eq!(one_line_edit("a\r\nb\r\nc\r\n", "b", "B", 2), "a\r\nB\r\nc\r\n");
        assert_eq!(one_line_edit("a\nb", "a", "A", 1), "A\nb");
    }
}
