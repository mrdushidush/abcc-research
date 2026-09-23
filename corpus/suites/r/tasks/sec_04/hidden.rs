#[cfg(test)]
mod w8_hidden {
    use super::*;

    fn gone(input: &str, secret: &str) {
        let out = redact(input);
        assert!(!out.contains(secret), "survived redaction: {input:?} -> {out:?}");
        assert!(out.contains("<redacted"), "no marker left in {out:?}");
    }

    #[test]
    fn a_telegram_bot_token_is_redacted() {
        gone(
            "token 123456789:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw0 saved",
            "AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw0",
        );
    }

    #[test]
    fn a_google_refresh_token_is_redacted() {
        gone(
            r#"{"refresh_token": "1//0gWXYZabcdefghijklmnopqrstuvwxyz0123456789"}"#,
            "0gWXYZabcdefghijklmnopqrstuvwxyz0123456789",
        );
    }

    #[test]
    fn a_google_client_secret_is_redacted() {
        gone(
            r#"{"client_secret": "GOCSPX-AbCdEfGhIjKlMnOpQrStUvWxYz12"}"#,
            "AbCdEfGhIjKlMnOpQrStUvWxYz12",
        );
    }

    #[test]
    fn env_var_secrets_are_redacted() {
        gone("BRAVE_API_KEY=BSAabcdefghijklmnopqrstuvwxyz12345", "BSAabcdefghijklmnopqrstuvwxyz12345");
        gone("GITHUB_TOKEN=opaque0123456789abcdefOPAQUE", "opaque0123456789abcdefOPAQUE");
    }

    #[test]
    fn an_aws_secret_key_is_redacted() {
        gone(
            "aws_secret_access_key = wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
        );
        gone(
            "AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
        );
    }

    #[test]
    fn ordinary_text_is_still_left_alone() {
        for clean in [
            "commit 3fdfefe12289b63b42e0502f516d41a1f8c59eed at 12:30:45",
            "the token: is refreshed daily, see docs/auth.md",
            "let key = map.get(&name);",
        ] {
            assert_eq!(redact(clean), clean, "clean text was changed");
        }
    }
}
