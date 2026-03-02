//! Write-Ahead Log (WAL) for incremental index updates.

use std::fs::{self, OpenOptions};
use std::io::{self, BufRead, BufReader, Write};
use std::path::{Path, PathBuf};

/// A single WAL entry representing an index update.
#[derive(Debug, Clone)]
pub enum WalEntry {
    /// Add or update a document
    Upsert {
        doc_id: u32,
        path: String,
        content_hash: String,
        tokens: Vec<String>,
    },
    /// Remove a document
    Delete { doc_id: u32 },
    /// Compact and create new snapshot
    Snapshot { version: u64 },
}

impl WalEntry {
    /// Serialize to string for WAL append.
    pub fn serialize(&self) -> String {
        match self {
            WalEntry::Upsert {
                doc_id,
                path,
                content_hash,
                tokens,
            } => {
                let tokens_str = tokens.join(",");
                format!("UPSERT|{}|{}|{}|{}", doc_id, path, content_hash, tokens_str)
            }
            WalEntry::Delete { doc_id } => {
                format!("DELETE|{}", doc_id)
            }
            WalEntry::Snapshot { version } => {
                format!("SNAPSHOT|{}", version)
            }
        }
    }

    /// Deserialize from WAL line.
    pub fn deserialize(line: &str) -> Option<Self> {
        let parts: Vec<&str> = line.split('|').collect();
        match parts.get(0)? {
            &"UPSERT" if parts.len() >= 5 => {
                let doc_id = parts[1].parse().ok()?;
                let path = parts[2].to_string();
                let content_hash = parts[3].to_string();
                let tokens = parts[4].split(',').map(|s| s.to_string()).collect();
                Some(WalEntry::Upsert {
                    doc_id,
                    path,
                    content_hash,
                    tokens,
                })
            }
            &"DELETE" if parts.len() >= 2 => {
                let doc_id = parts[1].parse().ok()?;
                Some(WalEntry::Delete { doc_id })
            }
            &"SNAPSHOT" if parts.len() >= 2 => {
                let version = parts[1].parse().ok()?;
                Some(WalEntry::Snapshot { version })
            }
            _ => None,
        }
    }
}

/// WAL manager for append-only log and compaction.
pub struct WalManager {
    wal_path: PathBuf,
    snapshot_dir: PathBuf,
    current_version: u64,
    entry_count: u64,
    compaction_threshold: u64,
}

impl WalManager {
    /// Create new WAL manager.
    pub fn new<P: AsRef<Path>, Q: AsRef<Path>>(wal_path: P, snapshot_dir: Q) -> io::Result<Self> {
        Self::new_with_threshold(wal_path, snapshot_dir, 1000)
    }

    /// Create WAL manager with custom compaction threshold.
    pub fn new_with_threshold<P: AsRef<Path>, Q: AsRef<Path>>(
        wal_path: P,
        snapshot_dir: Q,
        compaction_threshold: u64,
    ) -> io::Result<Self> {
        let wal_path = wal_path.as_ref().to_path_buf();
        let snapshot_dir = snapshot_dir.as_ref().to_path_buf();

        fs::create_dir_all(&snapshot_dir)?;

        let entry_count = if wal_path.exists() {
            Self::count_entries(&wal_path)?
        } else {
            0
        };

        Ok(WalManager {
            wal_path,
            snapshot_dir,
            current_version: 0,
            entry_count,
            compaction_threshold: compaction_threshold.max(1),
        })
    }

    /// Append entry to WAL.
    pub fn append(&mut self, entry: &WalEntry) -> io::Result<()> {
        let mut file = OpenOptions::new()
            .create(true)
            .append(true)
            .open(&self.wal_path)?;

        writeln!(file, "{}", entry.serialize())?;
        self.entry_count += 1;

        // Auto-trigger compaction check
        if self.entry_count >= self.compaction_threshold {
            // Compaction would be triggered here in full implementation
        }

        Ok(())
    }

    /// Replay WAL entries.
    pub fn replay(&self) -> io::Result<Vec<WalEntry>> {
        if !self.wal_path.exists() {
            return Ok(Vec::new());
        }

        let file = fs::File::open(&self.wal_path)?;
        let reader = BufReader::new(file);
        let mut entries = Vec::new();

        for line in reader.lines() {
            let line = line?;
            if let Some(entry) = WalEntry::deserialize(&line) {
                entries.push(entry);
            }
        }

        Ok(entries)
    }

    /// Create snapshot marker.
    pub fn create_snapshot_marker(&mut self) -> io::Result<()> {
        self.current_version += 1;

        // Append snapshot marker to WAL
        self.append(&WalEntry::Snapshot {
            version: self.current_version,
        })?;

        Ok(())
    }

    /// Compact WAL by truncating log after snapshot.
    pub fn compact(&mut self) -> io::Result<PathBuf> {
        self.current_version += 1;
        let snapshot_path = self
            .snapshot_dir
            .join(format!("snapshot_v{}.wal", self.current_version));

        // Copy current WAL to snapshot
        if self.wal_path.exists() {
            fs::copy(&self.wal_path, &snapshot_path)?;
        }

        // Append snapshot marker
        self.append(&WalEntry::Snapshot {
            version: self.current_version,
        })?;

        // Truncate WAL
        fs::write(&self.wal_path, "")?;
        self.entry_count = 0;

        Ok(snapshot_path)
    }

    /// Returns whether compaction should be triggered by threshold.
    pub fn should_compact(&self) -> bool {
        self.entry_count >= self.compaction_threshold
    }

    fn count_entries(wal_path: &Path) -> io::Result<u64> {
        if !wal_path.exists() {
            return Ok(0);
        }
        let file = fs::File::open(wal_path)?;
        let reader = BufReader::new(file);
        let count = reader.lines().count() as u64;
        Ok(count)
    }

    /// Get current stats.
    pub fn stats(&self) -> WalStats {
        WalStats {
            entry_count: self.entry_count,
            current_version: self.current_version,
            wal_path: self.wal_path.clone(),
        }
    }
}

/// WAL statistics.
#[derive(Debug)]
pub struct WalStats {
    pub entry_count: u64,
    pub current_version: u64,
    pub wal_path: PathBuf,
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::TempDir;

    #[test]
    fn test_wal_entry_serialize_deserialize() {
        let entry = WalEntry::Upsert {
            doc_id: 1,
            path: "test.rs".to_string(),
            content_hash: "abc123".to_string(),
            tokens: vec!["fn".to_string(), "main".to_string()],
        };

        let serialized = entry.serialize();
        let deserialized = WalEntry::deserialize(&serialized).unwrap();

        match deserialized {
            WalEntry::Upsert {
                doc_id,
                path,
                content_hash,
                tokens,
            } => {
                assert_eq!(doc_id, 1);
                assert_eq!(path, "test.rs");
                assert_eq!(content_hash, "abc123");
                assert_eq!(tokens, vec!["fn", "main"]);
            }
            _ => panic!("Expected Upsert entry"),
        }
    }

    #[test]
    fn test_wal_manager_append_replay() {
        let temp_dir = TempDir::new().unwrap();
        let wal_path = temp_dir.path().join("test.wal");
        let snapshot_dir = temp_dir.path().join("snapshots");

        let mut manager = WalManager::new(&wal_path, &snapshot_dir).unwrap();

        // Append entries
        let entry1 = WalEntry::Upsert {
            doc_id: 1,
            path: "a.rs".to_string(),
            content_hash: "hash1".to_string(),
            tokens: vec!["fn".to_string()],
        };
        let entry2 = WalEntry::Delete { doc_id: 1 };

        manager.append(&entry1).unwrap();
        manager.append(&entry2).unwrap();

        // Replay
        let replayed = manager.replay().unwrap();
        assert_eq!(replayed.len(), 2);

        // Check stats
        let stats = manager.stats();
        assert_eq!(stats.entry_count, 2);
    }

    #[test]
    fn test_wal_compaction() {
        let temp_dir = TempDir::new().unwrap();
        let wal_path = temp_dir.path().join("test.wal");
        let snapshot_dir = temp_dir.path().join("snapshots");

        let mut manager = WalManager::new(&wal_path, &snapshot_dir).unwrap();

        // Append some entries
        for i in 0..5 {
            let entry = WalEntry::Upsert {
                doc_id: i,
                path: format!("file{}.rs", i),
                content_hash: format!("hash{}", i),
                tokens: vec![],
            };
            manager.append(&entry).unwrap();
        }

        // Compact
        let snapshot_path = manager.compact().unwrap();
        assert!(snapshot_path.exists());

        // WAL should be empty after compaction
        let stats = manager.stats();
        assert_eq!(stats.entry_count, 0);
        assert_eq!(stats.current_version, 1);
    }
}
