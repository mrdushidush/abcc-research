#[cfg(test)]
mod w8_hidden {
    use super::*;
    use std::path::PathBuf;

    fn walk_scratch(label: &str) -> PathBuf {
        let dir = std::env::temp_dir().join("w8-hidden-shell06").join(format!(
            "{label}-{}-{}",
            std::process::id(),
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .map_or(0, |d| d.as_nanos())
        ));
        std::fs::create_dir_all(&dir).unwrap();
        dir
    }

    #[test]
    fn walk_respects_gitignore() {
        let dir = walk_scratch("gitignore");
        std::fs::create_dir_all(dir.join(".git")).unwrap();
        std::fs::write(dir.join(".gitignore"), "ignored.rs\n").unwrap();
        std::fs::write(dir.join("kept.rs"), "fn kept() {}\n").unwrap();
        std::fs::write(dir.join("ignored.rs"), "fn ignored() {}\n").unwrap();

        let mut seen: Vec<String> = Vec::new();
        walk(&dir, &mut |path: &Path| {
            seen.push(path.file_name().unwrap().to_string_lossy().into_owned());
            true
        });

        assert!(seen.contains(&"kept.rs".to_string()), "got: {seen:?}");
        assert!(
            !seen.contains(&"ignored.rs".to_string()),
            "a .gitignore'd file was scanned: {seen:?}"
        );
    }

    #[test]
    fn walk_stops_the_whole_walk_when_the_callback_returns_false() {
        let dir = walk_scratch("stop");
        for sub in ["a", "b", "c"] {
            let child = dir.join(sub);
            std::fs::create_dir_all(&child).unwrap();
            std::fs::write(child.join("f.rs"), "fn f() {}\n").unwrap();
        }

        let mut count = 0usize;
        walk(&dir, &mut |_path: &Path| {
            count += 1;
            false
        });

        assert_eq!(count, 1, "the first `false` must end the walk; got {count} callbacks");
    }
}
