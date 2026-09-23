#[cfg(test)]
mod w8_hidden {
    use super::*;
    use crate::clock::MockClock;

    #[test]
    fn two_ids_minted_at_the_same_instant_differ() {
        let now = Utc.with_ymd_and_hms(2026, 4, 21, 10, 0, 0).unwrap();
        let a = new_id(now);
        let b = new_id(now);
        assert_ne!(a, b, "same instant, same id");
        assert!(a.starts_with("sch_") && b.starts_with("sch_"), "got {a} and {b}");
    }

    #[test]
    fn cancelling_one_of_two_entries_made_in_one_tick_keeps_the_other() {
        let path = std::env::temp_dir().join(format!(
            "w8-hidden-sched02-{}.jsonl",
            std::process::id()
        ));
        let _ = std::fs::remove_file(&path);
        let clock = Arc::new(MockClock::new(
            Utc.with_ymd_and_hms(2026, 4, 21, 10, 0, 0).unwrap(),
        ));
        let mut s = Scheduler::new(path.clone(), clock);

        let first = s.add("in 30 minutes", "first".into(), None, None).unwrap();
        let second = s.add("in 45 minutes", "second".into(), None, None).unwrap();
        assert_ne!(first.id, second.id, "two entries in one tick share an id");

        assert!(s.cancel(&first.id).unwrap(), "cancel found nothing");
        let left: Vec<&str> = s.list().iter().map(|e| e.prompt.as_str()).collect();
        let _ = std::fs::remove_file(&path);
        assert_eq!(left, vec!["second"], "cancelling one entry removed both");
    }
}
