//! Unicode-aware tokenizer with snake/camel splitting.

const COMPOUND_PREFIXES: &[&str] = &[
    "https", "http", "json", "yaml", "url", "api", "xml", "tls", "ssl", "tcp", "udp",
];

const COMPOUND_SUFFIXES: &[&str] = &[
    "config",
    "option",
    "error",
    "retry",
    "path",
    "url",
    "version",
    "main",
    "test",
    "type",
    "name",
    "file",
    "line",
    "data",
    "item",
    "client",
    "server",
    "glob",
    "parse",
];

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
                out.push(lowered.clone());
                if let Some((head, tail)) = split_compound_token(&lowered) {
                    if head.len() >= 2 && head != lowered {
                        out.push(head);
                    }
                    if tail.len() >= 2 && tail != lowered {
                        out.push(tail);
                    }
                }
            }
        }
    }
}

fn split_compound_token(token: &str) -> Option<(String, String)> {
    let lower = token.to_ascii_lowercase();

    for suffix in COMPOUND_SUFFIXES {
        if !lower.ends_with(suffix) {
            continue;
        }
        let head_len = lower.len().saturating_sub(suffix.len());
        if head_len < 3 {
            continue;
        }
        let head = &lower[..head_len];
        if head.chars().all(|c| c.is_ascii_alphabetic()) {
            return Some((head.to_string(), (*suffix).to_string()));
        }
    }

    for prefix in COMPOUND_PREFIXES {
        if !lower.starts_with(prefix) {
            continue;
        }
        let tail = &lower[prefix.len()..];
        if tail.len() < 3 {
            continue;
        }
        if tail.chars().all(|c| c.is_ascii_alphabetic()) {
            return Some(((*prefix).to_string(), tail.to_string()));
        }
    }

    None
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

    #[test]
    fn splits_compound_prefix_and_suffix() {
        let got = tokenize("tool_urlglob parseURL HTTPClient");
        assert!(got.contains(&"urlglob".to_string()));
        assert!(got.contains(&"url".to_string()));
        assert!(got.contains(&"glob".to_string()));
        assert!(got.contains(&"parse".to_string()));
        assert!(got.contains(&"http".to_string()));
        assert!(got.contains(&"client".to_string()));
    }
}
