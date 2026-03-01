//! Deterministic BM25 scorer.

/// Compute BM25 score.
pub fn score(
    tf: u32,
    doc_len: f64,
    avg_doc_len: f64,
    doc_freq: usize,
    total_docs: usize,
    k1: f64,
    b: f64,
) -> f64 {
    if tf == 0 || doc_freq == 0 || total_docs == 0 {
        return 0.0;
    }

    let tf_f = tf as f64;
    let df_f = doc_freq as f64;
    let n_f = total_docs as f64;

    let idf = ((n_f - df_f + 0.5) / (df_f + 0.5) + 1.0).ln();
    let norm = 1.0 - b + b * (doc_len / avg_doc_len.max(1.0));
    let num = tf_f * (k1 + 1.0);
    let den = tf_f + k1 * norm;

    idf * (num / den.max(1e-9))
}

#[cfg(test)]
mod tests {
    use super::score;

    #[test]
    fn bm25_is_positive_when_match_exists() {
        let s = score(3, 100.0, 80.0, 10, 1000, 1.2, 0.75);
        assert!(s > 0.0);
    }
}
