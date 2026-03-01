//! Unicode-aware tokenizer with snake/camel splitting.

/// Tokenize source text into lowercase lexical terms.
pub fn tokenize(text: &str) -> Vec<String> {
    let mut out: Vec<String> = Vec::new();
    let mut buf = String::new();

    for ch in text.chars() {
        if ch.is_alphanumeric() || ch == '_' {
            buf.push(ch);
        } else if !buf.is_empty() {
            push_token(&buf, &mut out);
            buf.clear();
        }
    }

    if !buf.is_empty() {
        push_token(&buf, &mut out);
    }

    out
}

fn push_token(token: &str, out: &mut Vec<String>) {
    for snake_part in token.split('_') {
        if snake_part.is_empty() {
            continue;
        }
        for part in split_camel_digit(snake_part) {
            let lowered = part.to_lowercase();
            if lowered.len() >= 2 {
                out.push(lowered);
            }
        }
    }
}

fn split_camel_digit(token: &str) -> Vec<&str> {
    if token.is_empty() {
        return Vec::new();
    }

    let mut parts: Vec<&str> = Vec::new();
    let mut start = 0usize;
    let chars: Vec<(usize, char)> = token.char_indices().collect();

    for i in 1..chars.len() {
        let (_, prev) = chars[i - 1];
        let (idx, curr) = chars[i];
        let boundary = (prev.is_lowercase() && curr.is_uppercase())
            || (prev.is_alphabetic() && curr.is_ascii_digit())
            || (prev.is_ascii_digit() && curr.is_alphabetic());
        if boundary {
            parts.push(&token[start..idx]);
            start = idx;
        }
    }

    parts.push(&token[start..]);
    parts
}

#[cfg(test)]
mod tests {
    use super::tokenize;

    #[test]
    fn splits_snake_and_camel() {
        let got = tokenize("handle_request HTTPServer2 token_v1");
        assert!(got.contains(&"handle".to_string()));
        assert!(got.contains(&"request".to_string()));
        assert!(got.contains(&"httpserver".to_string()) || got.contains(&"http".to_string()));
        assert!(got.contains(&"token".to_string()));
    }
}
