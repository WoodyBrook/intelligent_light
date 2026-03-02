# Advanced AI Feature Specification
**Version**: 1.1 (Clean Room Implementation Guide)
**Target**: Engineering Team

This document outlines the technical specifications for four advanced features identified in the reference implementation. Implementers should follow these logic patterns and data structures while using their own code style and best practices.

---

## 1. Ontology Entity Registry (Memory Structure)

### 1.1 Core Concept
A structured memory system that goes beyond simple vector similarity. It maintains a graph-like registry of unique entities (People, Places, Events, Objects) to solve the "Hallucination" and "Amnesia" problems in long conversations.

### 1.2 Data Structures

#### Entity Types
Define a standardized Enum for entity types:
*   `PERSON`: Human beings.
*   `PLACE`: Physical locations.
*   `EVENT`: Occurrences (e.g., "The release of DeepSeek").
*   `OBJECT`: Physical items (e.g., "My red coffee mug").
*   `TIME`: Abstract time concepts.

#### Entity Model
```json
{
  "id": "UUID string",
  "type": "EntityType",
  "name": "Primary canonical name (e.g., 'Li Lei')",
  "aliases": ["List of strings (e.g., 'Xiao Li', 'Manager Li')"],
  "attributes": "Key-Value pairs (Dynamic attributes)",
  "relations": [
    {
      "type": "Relation type (e.g., 'friend_of')",
      "target_id": "UUID of target entity"
    }
  ],
  "mention_count": "Integer",
  "last_mentioned": "Timestamp"
}
```

### 1.3 Ingestion Logic (The Missing Link)

#### Asynchronous Extraction Pipeline
Do **NOT** run NER on the critical path (blocking response). Implement an async event-driven pipeline:
1.  **Trigger**: On every user message completion.
2.  **Job**: Push `(user_input, assistant_response)` to a queue (e.g., Celery/Redis).
3.  **LLM Extraction**:
    *   **Prompt**: "Identify entities (Person, Place, etc.) in the text. Return JSON list. For each entity, checks if it matches an alias in the providing 'Existing Entity Snippets' list."
    *   **Context**: Provide names/aliases of the top 20 most recently accessed entities to the LLM to help it perform "Soft De-duplication" during extraction.
4.  **Consolidation (Registry Logic)**:
    *   If LLM returns ID of an existing entity: Update `last_mentioned` and `attributes`.
    *   If LLM returns a new entity:
        *   **Hard De-duplication**: Check strict string equality on Name/Alias against DB.
        *   **Embedding Check (Optional)**: If similarity(new_name_embedding, existing_name_embedding) > 0.95, flag for manual review or merge.
        *   Create new ID if unique.

### 1.4 Reference Resolution (Consumption)
To support natural language like "He said...", implement a `resolve_reference` function:
1.  **Input**: `reference_string` (e.g., "he").
2.  **Pronoun Map**: Map terms like "he" -> PERSON.
3.  **Stack Search**: Pop from `recent_entities` stack. First match of correct Type wins.
4.  **Fallback**: If not a pronoun, try Alias check -> Fuzzy String Match.

---

## 2. MCP Manager (Model Context Protocol)

### 2.1 Core Concept
Standardize external tools (File system, GitHub, database) into a unified format.

### 2.2 Proactive Event Criteria
To avoid "Privacy Invasion" and "Token Waste", define strict "Significant Change" criteria.

#### Email "Importance" Definition
Do **NOT** send every email to the LLM. Use a **Tiered Filter**:
1.  **Tier 1 (Metadata)**:
    *   Headers: `X-Priority: High` or `Importance: High`.
    *   Provider Flags: `\Flagged` (IMAP) or `is:important` (Gmail API).
    *   **Pass Condition**: If true, treat as important immediately.
2.  **Tier 2 (Heuristics)**:
    *   Whitelist: Sender domain in `@company.com` or specific VIP list.
    *   **Pass Condition**: If true, treat as important.
3.  **Tier 3 (LLM Sampling - Optional & Rate Limited)**:
    *   Only for unread emails from "Known Contacts" (in Address Book) but not in whitelist.
    *   **Prompt**: "Classify if this email requires immediate user action (e.g., bill payment, meeting change). Output BOOLEAN only."

### 2.3 Architecture
*   **Client**: `StdioClient` or `SSEClient`.
*   **OAuth**: Standard Auth Code flow with `refresh_token` auto-renewal.

---

## 3. Hybrid Search (RAG Optimization)

### 3.1 Chinese Logic Adaptation
Standard BM25 libraries often default to space-splitting. For Chinese, you **MUST** integrate a segmenter.

#### Indexing Strategy
1.  **Tokenizer**:
    *   **Implementation**: Use `jieba` (accurate, lighter) or `hanlp` (neural, heavier).
    *   **Standard**: `jieba.cut_for_search(text)` (finer granularity for recall).
2.  **Persistence (The "Memory" Pitfall)**:
    *   ChromaDB does **NOT** persist BM25 indices.
    *   **Solution**: Since user memory is typically < 100MB text, maintain **In-Memory BM25** (using `rank_bm25` library).
    *   **Startup**: Load all documents from Chroma -> Tokenize -> Build BM25 RAM Index.
    *   **Incremental Update**: When adding 1 document, simple append to list is fast. Re-build index every N (e.g., 50) updates or on restart.

### 3.2 Weighted Fusion
$$ Score = (0.5 \times Vector_{norm}) + (0.5 \times BM25_{norm}) $$
*   **Recommendation**: Use Reciprocal Rank Fusion (RRF) if calibration is difficult.

---

## 4. Pattern Scanner (Automated Insight)

### 4.1 "Cold Start" & "Feedback Loop"
The system must learn from user corrections.

#### Negative Feedback (IgnoredPatterns)
1.  **Storage**: Maintain a `blacklist_patterns` JSON collection.
    *   Structure: `{"type": "monthly", "day": 10, "keyword": "hospital"}`.
2.  **Logic**: Before saving a candidate pattern, check:
    *   Does it match any blacklist rule?
    *   If yes, drop it silently.
3.  **UI Interaction**: When user says "This isn't a rule", create a blacklist entry derived from that pattern's attributes.

#### Semantic Clustering Logic
Do **NOT** use full sentence embeddings (too noisy).
1.  **Feature Extraction**:
    *   Use LLM to extract "Activity Tuple" from event text: `(Verb, Object)`.
    *   Example: "I went to the gym" -> `(go, gym)`.
2.  **Vectorize**: Embed only the `Object` or `Verb+Object`.
3.  **Clustering**:
    *   Use **DBSCAN** (density-based) instead of K-Means, as it doesn't require specifying 'K' (number of clusters) and handles noise better.
    *   Group events with high cosine similarity (> 0.85) in the feature space.

---
**End of Specification**
