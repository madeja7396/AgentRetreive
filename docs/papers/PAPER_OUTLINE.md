# AgentRetrieve: Paper Outline

## Title
**AgentRetrieve: Non-Embedding, Deterministic Code Retrieval for LLM Agents**

## Abstract
Large Language Model (LLM) agents for software engineering rely heavily on code search tools, yet existing tools are designed for human developers, not agents. We propose AgentRetrieve, a code retrieval system that prioritizes tool-call efficiency and token economy over human readability. Unlike embedding-based semantic search, AgentRetrieve uses a deterministic BM25-based index with structured DSL input and mini-JSON output featuring capability handles (doc_id/span_id). Evaluation on 25 real-world tasks across 5 repositories shows 96% recall@5 and 0.61 MRR, with deterministic outputs and 80% estimated token reduction compared to traditional tools.

## 1. Introduction
- Problem: LLM agents use generic file tools (grep, cat, find) → excessive tool calls
- Gap: Existing code search optimized for human readability, not agent efficiency
- Solution: AgentRetrieve - agent-native code retrieval
- Key ideas: Non-embedding, deterministic, capability-based, budget-aware
- Contributions:
  1. Structured DSL for agent-generated queries
  2. Mini-JSON output contract with capability handles
  3. Deterministic BM25 scoring (0-1000 integer)
  4. Evaluation framework for agent retrieval

## 2. Background
- LLM agents for software engineering
- Code search tools (ripgrep, git grep, semantic search)
- Information retrieval basics (BM25, inverted index)

## 3. Method
### 3.1 Design Principles
- Non-embedding (deterministic, offline-capable)
- Capability-based (opaque handles, not full paths)
- Budget-aware (strict output limits)
- Proof-carrying (digest + bounds)

### 3.2 System Architecture
- Tokenizer (camelCase/snake_case aware)
- Inverted Index (file-granularity BM25)
- Query Engine (must/should/not constraints)
- Output Formatter (mini-JSON v1)

### 3.3 Input/Output Contracts
- DSL v1 schema
- Mini-JSON v1 schema
- Capability handle specification

## 4. Evaluation
### 4.1 Setup
- 5 repositories (ripgrep, fd, fzf, curl, fmt)
- 25 tasks (document search, configuration lookup)
- Metrics: Recall@K, MRR@K, Latency, Determinism

### 4.2 Results
- Retrieval quality: 96% recall@5, MRR=0.61
- Determinism: 100% (5 runs identical)
- Latency: 21-139ms (small-medium corpora)

### 4.3 Comparison
- vs ripgrep: Better ranking, structured output
- vs git grep: Better ranking, structured output
- vs semantic: Deterministic, faster, offline

## 5. Discussion
### 5.1 Limitations
- No semantic understanding (agent must decompose intent)
- Rename sensitivity
- Large corpus optimization needed

### 5.2 Future Work
- Symbol-level indexing
- Near-constraint (proximity search)
- Multi-hop retrieval chains

## 6. Conclusion
AgentRetrieve demonstrates that deterministic, non-embedding code retrieval can achieve high accuracy while being significantly more agent-efficient than traditional tools.

## References
- [BM25] Robertson et al., 1994
- [ripgrep] BurntSushi, 2020
- [SWE-agent] Princeton, 2024
- [CodeBERT] Feng et al., 2020

## Appendix
- A. DSL v1 Schema
- B. Mini-JSON v1 Schema
- C. Taskset Details
- D. Reproduction Instructions
