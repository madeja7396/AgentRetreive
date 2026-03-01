use std::io::{self, BufRead, Write};

use ar_core::{healthcheck, ENGINE_VERSION};
use serde_json::{json, Value};

fn main() {
    let stdin = io::stdin();
    let mut stdout = io::stdout();

    for line in stdin.lock().lines() {
        let Ok(raw) = line else {
            continue;
        };
        let trimmed = raw.trim();
        if trimmed.is_empty() {
            continue;
        }

        let Ok(req): Result<Value, _> = serde_json::from_str(trimmed) else {
            continue;
        };

        let id = req.get("id").cloned().unwrap_or(Value::Null);
        let method = req.get("method").and_then(Value::as_str).unwrap_or("");
        let params = req.get("params").cloned().unwrap_or_else(|| json!({}));

        let response = if method.is_empty() {
            json!({
                "jsonrpc": "2.0",
                "id": id,
                "error": {"code": -32600, "message": "invalid request"}
            })
        } else {
            json!({
                "jsonrpc": "2.0",
                "id": id,
                "result": dispatch(method, &params)
            })
        };

        let _ = writeln!(stdout, "{}", response);
        let _ = stdout.flush();
    }
}

fn dispatch(method: &str, params: &Value) -> Value {
    match method {
        "ar.search" => json!({
            "ok": true,
            "status": "bootstrap",
            "method": method,
            "engine": "rust",
            "engine_version": ENGINE_VERSION,
            "health": healthcheck(),
            "params_echo": params,
        }),
        "ar.read_span" | "ar.expand" | "ar.index_status" | "ar.callers" => json!({
            "ok": true,
            "status": "bootstrap",
            "method": method,
            "engine": "rust",
            "engine_version": ENGINE_VERSION,
            "health": healthcheck(),
            "params_echo": params,
        }),
        _ => json!({
            "ok": false,
            "status": "unsupported_method",
            "method": method,
            "engine": "rust",
            "engine_version": ENGINE_VERSION,
            "health": healthcheck(),
        }),
    }
}
