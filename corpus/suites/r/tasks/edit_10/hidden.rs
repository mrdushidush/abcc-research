#[cfg(test)]
mod w8_hidden {
    use super::*;

    struct Asked {
        seen: Vec<String>,
        allow: bool,
    }

    impl PermissionPrompter for Asked {
        fn decide(&mut self, request: &PermissionRequest) -> PermissionPromptDecision {
            self.seen.push(request.tool_name.clone());
            if self.allow {
                PermissionPromptDecision::Allow
            } else {
                PermissionPromptDecision::Deny {
                    reason: "operator said no".to_string(),
                }
            }
        }
    }

    fn policy() -> PermissionPolicy {
        PermissionPolicy::new(PermissionMode::Prompt)
            .with_tool_requirement("read_file", PermissionMode::ReadOnly)
            .with_tool_requirement("write_file", PermissionMode::WorkspaceWrite)
            .with_tool_requirement("bash", PermissionMode::DangerFullAccess)
    }

    #[test]
    fn prompt_mode_asks_before_a_dangerous_tool_and_honours_a_no() {
        let mut asked = Asked { seen: Vec::new(), allow: false };
        let outcome = policy().authorize("bash", "rm -rf build", Some(&mut asked));
        assert!(matches!(outcome, PermissionOutcome::Deny { .. }), "got {outcome:?}");
        assert_eq!(asked.seen, vec!["bash".to_string()]);
    }

    #[test]
    fn prompt_mode_asks_before_a_write_and_honours_a_yes() {
        let mut asked = Asked { seen: Vec::new(), allow: true };
        let outcome = policy().authorize("write_file", "{}", Some(&mut asked));
        assert_eq!(outcome, PermissionOutcome::Allow);
        assert_eq!(asked.seen, vec!["write_file".to_string()]);
    }

    #[test]
    fn prompt_mode_with_no_prompter_denies_instead_of_allowing() {
        let outcome = policy().authorize("bash", "echo hi", None);
        assert!(matches!(outcome, PermissionOutcome::Deny { .. }), "got {outcome:?}");
    }

    #[test]
    fn prompt_mode_still_allows_read_only_tools_without_asking() {
        let mut asked = Asked { seen: Vec::new(), allow: false };
        let outcome = policy().authorize("read_file", "{}", Some(&mut asked));
        assert_eq!(outcome, PermissionOutcome::Allow);
        assert!(asked.seen.is_empty(), "asked about a read: {:?}", asked.seen);
    }
}
