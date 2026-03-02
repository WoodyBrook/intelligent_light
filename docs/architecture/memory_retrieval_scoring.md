# Advanced Memory Retrieval Design (Weighted Scoring)

**Status**: Proposal
**Goal**: To implement a human-like memory retrieval system that balances relevance, recency, and importance, rather than relying solely on vector similarity.

## 1. The Core Algorithm
The "Memory Score" determines the probability of retrieving a specific memory $m$.

$$ \text{Score}(m) = \alpha \cdot \text{Relevance} + \beta \cdot \text{Recency} + \gamma \cdot \text{Importance} $$

### 1.1 Relevance (Vector Similarity)
- **Definition**: How semantically similar is the memory to the current query?
- **Implementation**: Cosine similarity between Query Vector and Memory Vector.
- **Range**: [0, 1] (Normalized from ChromaDB distance).

### 1.2 Recency (Exponential Decay)
- **Definition**: Recently accessed memories are easier to recall.
- **Formula**: $e^{-\frac{t_{now} - t_{base}}{\tau}}$
- **Time Baseline ($t_{base}$)**:
    - New Memory: `creation_time`
    - Retrieved Memory: `max(creation_time, last_accessed)`
    - *Purpose*: Prevents never-accessed but important old memories from fading too fast if they were just created but not queried.
- **Decay Factor ($\tau$)**: Controls how fast memories fade. Default $\tau \approx 72$ hours.

### 1.3 Importance (Significance Score)
- **Default**: $\alpha=0.5, \beta=0.3, \gamma=0.2$
- **Recency Boost**: If query contains "just now", "recently", "last time" → $\beta=0.6, \alpha=0.3, \gamma=0.1$
- **Importance Boost**: If query contains "important", "core", "forever" → $\gamma=0.5, \alpha=0.3, \beta=0.2$

## 2. Implementation Flow

### Phase 1: Storage (Writing)
When calling `save_user_memory`:
1.  **Extract & Rate**:
    - **Episodic**: Use `extract_episodic_memory` (includes importance).
    - **Preference**: Use `extract_user_preference` (default importance 5).
    - **Rules**: Check for high-value keywords.
2.  **Store**: Save to ChromaDB with metadata:
    ```json
    {
      "importance": 8,
      "last_accessed": 1704100000,
      "creation_time": 1704100000,
      "type": "episodic" // or "fact", "preference"
    }
    ```

### Phase 2: Retrieval (Reading)
When calling `retrieve_related_memories(query)`:
1.  **Intent Analysis (Dynamic Weights)**: Check query for time/importance keywords.
2.  **Vector Search**: Fetch Top-50 candidates via **Relevance**.
3.  **Re-Ranking**:
    - Calculate `Recency_Score` (using $t_{base}$).
    - Calculate `Importance_Score` (normalized).
    - Compute `Final_Score`.
4.  **Selection**: Sort and pick Top-K ($K=5$).
5.  **Reinforcement**: Update `last_accessed` for retrieved items.

## 3. Reference
This approach is inspired by the **Generative Agents** (Park et al., 2023) memory model.
