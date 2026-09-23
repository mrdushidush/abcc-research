#[cfg(test)]
mod w8_hidden {
    use super::*;
    use std::fs;

    fn grep(base: &std::path::Path, context: u64) -> Value {
        let input = json!({
            "pattern": "needle",
            "path": base.to_str().unwrap(),
            "context": context
        })
        .to_string();
        serde_json::from_str(&run_grep_search(&input).unwrap()).unwrap()
    }

    fn fixture(label: &str) -> std::path::PathBuf {
        let base = user_home()
            .join(".claudette")
            .join("files")
            .join(format!("w8-hidden-shell07-{label}"));
        let _ = fs::remove_dir_all(&base);
        fs::create_dir_all(&base).unwrap();
        // 100 matches, 25 lines apart, so no two context windows overlap.
        let mut body = String::new();
        for i in 0..2500 {
            if i % 25 == 12 {
                body.push_str(&format!("needle {i}\n"));
            } else {
                body.push_str(&format!("filler line {i}\n"));
            }
        }
        fs::write(base.join("big.txt"), body).unwrap();
        base
    }

    #[test]
    fn context_mode_caps_the_total_lines_it_returns() {
        let _eg = crate::test_env_lock();
        let base = fixture("cap");
        let v = grep(&base, 10);
        let _ = fs::remove_dir_all(&base);
        let n = v["matches"].as_array().unwrap().len();
        assert!(n <= 600, "context mode returned {n} lines; the cap is 600");
        assert!(n >= 500, "the cap should still return a useful amount, got {n}");
        assert_eq!(v["truncated"], json!(true), "a capped result must say truncated");
    }

    #[test]
    fn a_small_context_result_is_not_truncated() {
        let _eg = crate::test_env_lock();
        let base = user_home()
            .join(".claudette")
            .join("files")
            .join("w8-hidden-shell07-small");
        let _ = fs::remove_dir_all(&base);
        fs::create_dir_all(&base).unwrap();
        fs::write(base.join("a.txt"), "aaa\nbbb\nneedle ccc\nddd\neee\n").unwrap();
        let v = grep(&base, 2);
        let _ = fs::remove_dir_all(&base);
        assert_eq!(v["matches"].as_array().unwrap().len(), 5);
        assert_eq!(v["truncated"], json!(false));
    }
}
