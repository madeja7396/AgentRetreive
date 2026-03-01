//! Symbol extraction with tree-sitter-first strategy.

use regex::Regex;
use serde::{Deserialize, Serialize};
use tree_sitter::{Parser, Query, QueryCursor};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SymbolSpan {
    pub name: String,
    pub kind: String,
    pub start_line: u32,
    pub end_line: u32,
}

/// Extract symbols from source text.
///
/// Python uses tree-sitter. Other languages use a regex fallback.
pub fn extract_symbols(lang_hint: Option<&str>, source: &str) -> Vec<SymbolSpan> {
    match lang_hint {
        Some("python") => {
            extract_python_symbols(source).unwrap_or_else(|| extract_fallback(source))
        }
        _ => extract_fallback(source),
    }
}

fn extract_python_symbols(source: &str) -> Option<Vec<SymbolSpan>> {
    let mut parser = Parser::new();
    let lang = tree_sitter_python::language();
    parser.set_language(&lang).ok()?;

    let tree = parser.parse(source, None)?;
    let query_src = r#"
(function_definition name: (identifier) @fn_name)
(class_definition name: (identifier) @class_name)
"#;

    let query = Query::new(&lang, query_src).ok()?;
    let capture_names = query.capture_names();
    let mut cursor = QueryCursor::new();
    let mut out: Vec<SymbolSpan> = Vec::new();

    for m in cursor.matches(&query, tree.root_node(), source.as_bytes()) {
        for c in m.captures {
            let cap_name = *capture_names.get(c.index as usize)?;
            let node = c.node;
            let text = node.utf8_text(source.as_bytes()).ok()?.to_string();
            let kind = if cap_name == "fn_name" {
                "function"
            } else {
                "class"
            };
            out.push(SymbolSpan {
                name: text,
                kind: kind.to_string(),
                start_line: (node.start_position().row as u32) + 1,
                end_line: (node.end_position().row as u32) + 1,
            });
        }
    }

    Some(out)
}

fn extract_fallback(source: &str) -> Vec<SymbolSpan> {
    let mut out: Vec<SymbolSpan> = Vec::new();
    let re = Regex::new(r"(?m)^\s*(def|class)\s+([A-Za-z_][A-Za-z0-9_]*)").expect("regex");

    for caps in re.captures_iter(source) {
        let Some(kind_m) = caps.get(1) else {
            continue;
        };
        let Some(name_m) = caps.get(2) else {
            continue;
        };
        let line = line_number_at(source, name_m.start());
        out.push(SymbolSpan {
            name: name_m.as_str().to_string(),
            kind: kind_m.as_str().to_string(),
            start_line: line,
            end_line: line,
        });
    }

    out
}

fn line_number_at(source: &str, byte_offset: usize) -> u32 {
    let prefix = &source[..byte_offset.min(source.len())];
    (prefix.bytes().filter(|b| *b == b'\n').count() as u32) + 1
}

#[cfg(test)]
mod tests {
    use super::extract_symbols;

    #[test]
    fn extracts_python_symbols() {
        let src = "class App:\n    pass\n\ndef run():\n    return 1\n";
        let symbols = extract_symbols(Some("python"), src);
        assert!(symbols.iter().any(|s| s.name == "App"));
        assert!(symbols.iter().any(|s| s.name == "run"));
    }
}
