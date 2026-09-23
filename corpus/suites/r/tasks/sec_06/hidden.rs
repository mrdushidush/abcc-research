#[cfg(test)]
mod w8_hidden {
    use super::*;

    #[test]
    fn walk_skips_dotenv_like_every_other_dotfile() {
        let dir = std::env::temp_dir().join("w8-hidden-sec06");
        let _ = std::fs::remove_dir_all(&dir);
        std::fs::create_dir_all(&dir).unwrap();
        std::fs::write(dir.join(".env"), "SECRET=hunter2\n").unwrap();
        std::fs::write(dir.join("ok.rs"), "fn main() {}\n").unwrap();

        let mut seen: Vec<String> = Vec::new();
        walk(&dir, &mut |p: &Path| {
            seen.push(p.file_name().unwrap().to_string_lossy().into_owned());
            true
        });
        let _ = std::fs::remove_dir_all(&dir);

        assert!(seen.contains(&"ok.rs".to_owned()), "walk found nothing: {seen:?}");
        assert!(
            !seen.contains(&".env".to_owned()),
            ".env was walked into model context: {seen:?}"
        );
    }
}
