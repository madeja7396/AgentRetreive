# Related Work

## 1. Code Search Tools

### 1.1 Syntax-Aware Tools
- **rg (ripgrep)** [BurntSushi, 2020]: Fast regex-based search, human-readable output
- **git grep**: Git-integrated regex search
- **ag (The Silver Searcher)**: Ack-like search with speed improvements

**Limitation**: Output designed for human consumption, not optimized for LLM agents.

### 1.2 Semantic Code Search
- **GrepAI** [Bernabeu, 2024]: Embedding-based semantic search for code
- **mgrep**: Multi-modal grep with semantic understanding

**Limitation**: Requires embedding computation, non-deterministic, API-dependent.

## 2. LLM Tool Use

### 2.1 Agent Frameworks
- **OpenAI Functions**: Structured tool calling for LLMs
- **LangChain Tools**: Composable tool chains for agents
- **Anthropic Computer Use**: General computer control via LLM

**Gap**: Existing tools are general-purpose, not optimized for code retrieval efficiency.

### 2.2 Code Agents
- **SWE-agent** [Princeton, 2024]: Agent for software engineering tasks
- **OpenHands** [OpenDevin]: General-purpose coding agent
- **Devin** [Cognition AI]: End-to-end software engineer

**Gap**: Use generic file tools (cat, grep, find) leading to excessive tool calls.

## 3. Information Retrieval for Code

### 3.1 Traditional IR
- **TF-IDF**: Term frequency-inverse document frequency
- **BM25** [Robertson et al., 1994]: Probabilistic retrieval model

**Adoption**: AgentRetrieve uses BM25 for deterministic, explainable scoring.

### 3.2 Neural Code Search
- **CodeBERT** [Feng et al., 2020]: Pre-trained model for code understanding
- **GraphCodeBERT** [Guo et al., 2021]: Code structure-aware embeddings

**Limitation**: Computationally expensive, non-deterministic, requires GPU.

## 4. Differentiation

| Aspect | Traditional | Neural | AgentRetrieve |
|--------|-------------|--------|---------------|
| **Speed** | Fast | Slow | Fast |
| **Deterministic** | Yes | No | Yes |
| **Offline** | Yes | No* | Yes |
| **Token Efficiency** | Low | Medium | High |
| **Agent-Native** | No | No | Yes |

*Neural methods often require API calls or GPU inference

## 5. Positioning

AgentRetrieve fills the gap between:
- **Fast deterministic tools** (ripgrep) that are not agent-optimized
- **Semantic neural tools** that are slow and non-deterministic

By designing specifically for LLM agents with capability-based output and strict budget controls, AgentRetrieve achieves both efficiency and determinism.
