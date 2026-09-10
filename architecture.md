# Technical Architecture & Production Design Document
**GraphOne / FrontierAtlas Intelligence Graph Ingestion Pipeline**

---

## 1. Scale Strategy (500,000+ Record Extraction)
To scale data acquisition to **500,000+ startups, products, and research papers** without manual intervention:
- **Distributed Async Worker Architecture**: Stateless worker nodes running Python `asyncio` and `httpx` containerized on Kubernetes (EKS/GKE) with Horizontal Pod Autoscaling (HPA).
- **Task Queue & Message Broker**: Apache Kafka or RabbitMQ partitioning URLs across thousands of crawler topics based on domain hash (`hash(domain) % partitions`), preventing single-domain bottlenecking.
- **Proxy Mesh & Anti-Bot Strategy**: Integration of residential proxy rotation (BrightData/ScraperAPI), headless Playwright rendering clusters for JavaScript-heavy targets, and TLS fingerprint spoofing (`curl-cffi`).
- **Distributed Storage Pipelines**: Async bulk copy (`COPY FROM STDIN` via `asyncpg`) into PostgreSQL staging tables.

---

## 2. Handling 413 Payload Overflows & 429 Rate Limits
- **413 Payload Too Large Mitigation**:
  - **Sliding-Window Semantic Truncation**: Strips HTML tags (`BeautifulSoup`) and retains semantic headers plus dense metadata payloads, bounding context windows to < 4,000 tokens.
  - **Hierarchical Text Summarization**: Sub-chunks long text before LLM submission.
- **429 Rate Limit Management**:
  - **Multi-Tier Fallback Matrix**: `Tier 1: Gemini 1.5 Flash` -> `Tier 2: Groq Llama 3` -> `Tier 3: Local Deterministic Structural Extractor`.
  - **Exponential Backoff with Full Jitter**:
    $$T_{backoff} = \min(T_{max}, T_{base} \cdot 2^{retry}) + \text{random}(0, \text{jitter})$$
  - **Distributed Token Bucket & Circuit Breaker**: Managed centrally via Redis sliding window rate limiters.

---

## 3. Distributed Freshness & Deduplication Engine
- **Redis Bloom Filters**: High-performance, memory-efficient probabilistic filtering for fast URL lookup ($O(1)$ time complexity) across distributed crawler nodes.
- **SHA-256 Content Fingerprinting**: Hashes normalized full-text content (`SHA256(strip_whitespace(text))`) to ignore duplicate syndicated news articles or duplicate job postings.
- **Incremental Timestamp State**: Stores last-modified HTTP headers (`If-Modified-Since` / `ETag`) and indexes `published_date` in PostgreSQL TimescaleDB hyper-tables for 24-hour freshness queries.

---

## 4. Production Storage Architecture Matrix
| Data Layer | Engine Choice | Justification & Architecture Role |
| :--- | :--- | :--- |
| **Primary Relational DB** | PostgreSQL + TimescaleDB | Schema-enforced canonical entities, transactional consistency, time-series indexing for 24-hr signals. |
| **Graph Storage** | Neo4j / Amazon Neptune | High-performance graph traversal mapping multi-dimensional relationships: `(Startup)-[:PRODUCES]->(Product)`, `(Paper)-[:IMPLEMENTED_BY]->(Repo)`. |
| **Vector Database** | Qdrant / Milvus | Dense vector storage for research paper embeddings, semantic job matching, and LLM RAG pipelines. |
| **Caching & State** | Redis Enterprise | Real-time rate limit counters, Bloom filters, deduplication hashes, and Celery task state. |
