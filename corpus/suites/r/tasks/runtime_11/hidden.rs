#[cfg(test)]
mod w8_hidden {
    use super::*;

    #[test]
    fn counters_saturate_at_u32_max() {
        let mut tracker = UsageTracker::new();
        tracker.record(TokenUsage {
            input_tokens: u32::MAX,
            output_tokens: u32::MAX,
            cache_creation_input_tokens: u32::MAX,
            cache_read_input_tokens: u32::MAX,
        });
        tracker.record(TokenUsage {
            input_tokens: 1,
            output_tokens: 1,
            cache_creation_input_tokens: 1,
            cache_read_input_tokens: 1,
        });
        let cu = tracker.cumulative_usage();
        assert_eq!(cu.input_tokens, u32::MAX);
        assert_eq!(cu.output_tokens, u32::MAX);
        assert_eq!(cu.cache_creation_input_tokens, u32::MAX);
        assert_eq!(cu.cache_read_input_tokens, u32::MAX);
        assert_eq!(cu.total_tokens(), u32::MAX);
        assert_eq!(tracker.turns(), 2);
    }

    #[test]
    fn total_tokens_saturates_on_a_single_report() {
        let one = TokenUsage {
            input_tokens: u32::MAX,
            output_tokens: 7,
            cache_creation_input_tokens: 0,
            cache_read_input_tokens: 0,
        };
        assert_eq!(one.total_tokens(), u32::MAX);
    }
}
