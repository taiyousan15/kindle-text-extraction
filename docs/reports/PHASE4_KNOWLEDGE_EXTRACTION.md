# Phase 4: Knowledge Extraction Implementation

Complete implementation of knowledge extraction functionality for the Kindle OCR system.

## Overview

Phase 4 implements advanced knowledge extraction capabilities, including:

- **Phase 4-1**: LLM-based knowledge extraction (concepts, facts, processes, insights, actions)
- **Phase 4-2**: YAML/JSON/Markdown structured output formats
- **Phase 4-3**: Entity extraction (Named Entity Recognition with Japanese support)
- **Phase 4-4**: Relationship extraction and knowledge graph construction

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Knowledge Extraction                      │
├─────────────────────────────────────────────────────────────┤
│  Phase 4-1: Extract concepts, facts, processes, insights    │
│  Phase 4-2: Format as YAML/JSON/Markdown                    │
│  Phase 4-3: Extract entities (NER)                          │
│  Phase 4-4: Extract relationships, build knowledge graph    │
└─────────────────────────────────────────────────────────────┘
           ↓                    ↓                    ↓
    ┌──────────┐       ┌──────────────┐      ┌────────────┐
    │ LLM API  │       │  Database    │      │  Export    │
    │ (Claude/ │       │  (Knowledge  │      │  (YAML/    │
    │  GPT-4)  │       │   Table)     │      │   JSON/    │
    └──────────┘       └──────────────┘      │   MD/CSV)  │
                                              └────────────┘
```

## Files Created

### 1. Schemas (`app/schemas/knowledge.py`)

Comprehensive Pydantic schemas for:

- **Knowledge Extraction**:
  - `KnowledgeExtractRequest` / `KnowledgeExtractResponse`
  - `StructuredKnowledge` (concepts, facts, processes, insights, actions)
  - `Concept`, `Fact`, `Process`, `Insight`, `ActionItem`

- **Entity Extraction** (Phase 4-3):
  - `EntityExtractRequest` / `EntityExtractResponse`
  - `Entity`, `EntityType` (person, organization, location, technical_term, etc.)

- **Relationship Extraction** (Phase 4-4):
  - `RelationshipExtractRequest` / `RelationshipExtractResponse`
  - `Relationship`, `RelationType` (IS_A, CAUSES, PART_OF, etc.)

- **Knowledge Graph**:
  - `KnowledgeGraph`, `KnowledgeGraphNode`, `KnowledgeGraphEdge`

- **Output Formats**:
  - `OutputFormat` (YAML, JSON, Markdown, CSV)
  - `ExportFormat`, `ImportanceLevel`

### 2. Service (`app/services/knowledge_service.py`)

Core service implementing:

- **Knowledge Extraction** (`extract_knowledge`):
  - Extracts structured information from text
  - Supports multiple languages (Japanese/English)
  - Quality scoring (0.0-1.0)
  - Chunking for long documents

- **Entity Extraction** (`extract_entities`):
  - Named Entity Recognition (NER)
  - Japanese-aware tokenization
  - Confidence scoring
  - Deduplication

- **Relationship Extraction** (`extract_relationships`):
  - Extracts triplets (subject, predicate, object)
  - Multiple relation types
  - Citation tracking

- **Knowledge Graph** (`build_knowledge_graph`):
  - Constructs graph from entities and relationships
  - Node/edge generation
  - Metadata tracking

- **Format Conversion**:
  - `format_as_yaml()`: Human-readable hierarchical format
  - `format_as_json()`: Machine-readable API format
  - `format_as_markdown()`: Documentation-friendly format
  - `format_relationships_as_csv()`: Spreadsheet format for relations

- **Database Operations**:
  - `save_knowledge_to_db()`: Save to Knowledge table
  - `get_knowledge_by_id()`: Retrieve by ID
  - `get_knowledge_by_book_title()`: Retrieve by book title
  - `get_text_from_job()`: Get text from OCR job

### 3. API Endpoints (`app/api/v1/endpoints/knowledge.py`)

RESTful API endpoints:

#### Knowledge Extraction
- `POST /api/v1/knowledge/extract` - Extract knowledge from text/job
- `GET /api/v1/knowledge/{knowledge_id}` - Get knowledge by ID
- `GET /api/v1/knowledge/book/{book_title}` - Get knowledge for book
- `POST /api/v1/knowledge/{knowledge_id}/export` - Export as file

#### Entity Extraction (Phase 4-3)
- `POST /api/v1/knowledge/extract-entities` - Extract entities only

#### Relationship Extraction (Phase 4-4)
- `POST /api/v1/knowledge/extract-relations` - Extract relationships
- `POST /api/v1/knowledge/build-graph` - Build knowledge graph

#### Health Check
- `GET /api/v1/knowledge/health` - Service health check

### 4. Tests (`test_knowledge.py`)

Comprehensive test suite:

- **Unit Tests**:
  - Basic knowledge extraction
  - Entity extraction (Japanese + English)
  - Relationship extraction
  - Knowledge graph construction
  - YAML/JSON/Markdown formatting
  - CSV export
  - Database integration

- **API Tests**:
  - Knowledge extraction endpoint
  - Entity extraction endpoint
  - Relationship extraction endpoint
  - Knowledge graph endpoint

## API Usage Examples

### 1. Extract Knowledge from Text

```bash
curl -X POST "http://localhost:8000/api/v1/knowledge/extract" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "人工知能は近年急速に発展しており...",
    "book_title": "AI入門",
    "format": "yaml",
    "include_entities": true,
    "include_relationships": true,
    "language": "ja",
    "min_confidence": 0.7
  }'
```

Response:
```json
{
  "knowledge_id": 1,
  "book_title": "AI入門",
  "format": "yaml",
  "structured_data": {
    "book_title": "AI入門",
    "main_topics": ["人工知能", "機械学習"],
    "concepts": [
      {
        "name": "機械学習",
        "definition": "データから学習するアルゴリズム",
        "importance": "high"
      }
    ],
    "facts": [...],
    "processes": [...],
    "insights": [...],
    "action_items": [...],
    "entities": [...],
    "relationships": [...]
  },
  "yaml_text": "book_title: AI入門\n...",
  "quality_score": 0.85,
  "language": "ja",
  "token_usage": {
    "total": 500,
    "prompt": 400,
    "completion": 100
  },
  "processing_time": 5.5,
  "is_mock": false
}
```

### 2. Extract Knowledge from OCR Job

```bash
curl -X POST "http://localhost:8000/api/v1/knowledge/extract" \
  -H "Content-Type: application/json" \
  -d '{
    "job_id": "550e8400-e29b-41d4-a716-446655440000",
    "format": "json",
    "include_entities": true,
    "include_relationships": true
  }'
```

### 3. Extract Entities Only

```bash
curl -X POST "http://localhost:8000/api/v1/knowledge/extract-entities" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "GoogleとMicrosoftがAI技術を開発している。",
    "language": "ja",
    "entity_types": ["organization", "technical_term"],
    "min_confidence": 0.7
  }'
```

Response:
```json
{
  "entities": [
    {
      "name": "Google",
      "type": "organization",
      "description": "テクノロジー企業",
      "confidence": 0.95
    },
    {
      "name": "Microsoft",
      "type": "organization",
      "confidence": 0.95
    },
    {
      "name": "AI技術",
      "type": "technical_term",
      "confidence": 0.90
    }
  ],
  "total_count": 3,
  "by_type": {
    "organization": 2,
    "technical_term": 1
  },
  "language": "ja",
  "processing_time": 2.5
}
```

### 4. Extract Relationships

```bash
curl -X POST "http://localhost:8000/api/v1/knowledge/extract-relations" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "機械学習は人工知能の一種である。",
    "language": "ja",
    "min_confidence": 0.7
  }'
```

Response:
```json
{
  "relationships": [
    {
      "subject": "機械学習",
      "predicate": "is_a",
      "object": "人工知能",
      "confidence": 0.9,
      "source_text": "機械学習は人工知能の一種である。"
    }
  ],
  "total_count": 1,
  "by_type": {
    "is_a": 1
  },
  "processing_time": 3.5
}
```

### 5. Build Knowledge Graph

```bash
curl -X POST "http://localhost:8000/api/v1/knowledge/build-graph" \
  -H "Content-Type: application/json" \
  -d '{
    "job_id": "550e8400-e29b-41d4-a716-446655440000",
    "min_confidence": 0.7
  }'
```

Response:
```json
{
  "nodes": [
    {
      "id": "ml_123",
      "label": "機械学習",
      "type": "technical_term",
      "properties": {
        "description": "データから学習",
        "confidence": 0.95
      }
    }
  ],
  "edges": [
    {
      "source": "ml_123",
      "target": "ai_456",
      "type": "is_a",
      "confidence": 0.9
    }
  ],
  "metadata": {
    "book_title": "AI入門",
    "node_count": 10,
    "edge_count": 8
  }
}
```

### 6. Export Knowledge

```bash
curl -X POST "http://localhost:8000/api/v1/knowledge/1/export" \
  -H "Content-Type: application/json" \
  -d '{
    "format": "yaml",
    "include_metadata": true
  }' \
  --output knowledge.yaml
```

## Output Format Examples

### YAML Format (Phase 4-2)

```yaml
book_title: AI入門
main_topics:
  - 人工知能
  - 機械学習
  - 深層学習
concepts:
  - name: 機械学習
    definition: データから学習するアルゴリズムの総称
    importance: high
    page_number: 10
  - name: 深層学習
    definition: 多層ニューラルネットワークを使用した学習
    importance: high
facts:
  - statement: AI市場は2025年までに1000億ドルに達する
    source_page: 15
    confidence: 0.9
processes:
  - name: 機械学習の実装手順
    steps:
      - 問題を明確に定義する
      - データを収集・準備する
      - モデルを選択し訓練する
      - 結果を評価し改善する
    description: 一般的な機械学習プロジェクトの流れ
insights:
  - text: AIは人間の能力を補完し、創造的な仕事に集中できる
    category: future_trends
    importance: high
action_items:
  - action: AIツールを試してみる
    priority: medium
    context: 実践的な理解を深めるため
entities:
  - name: Google
    type: organization
    confidence: 0.95
relationships:
  - subject: 機械学習
    predicate: is_a
    object: 人工知能
    confidence: 0.9
```

### JSON Format (Phase 4-2)

```json
{
  "book_title": "AI入門",
  "main_topics": ["人工知能", "機械学習"],
  "concepts": [
    {
      "name": "機械学習",
      "definition": "データから学習するアルゴリズム",
      "importance": "high"
    }
  ],
  "facts": [...],
  "processes": [...],
  "insights": [...],
  "action_items": [...],
  "entities": [...],
  "relationships": [...]
}
```

### Markdown Format (Phase 4-2)

```markdown
# AI入門

## 主要トピック
- 人工知能
- 機械学習
- 深層学習

## 概念
### 機械学習 (high)
データから学習するアルゴリズムの総称

### 深層学習 (high)
多層ニューラルネットワークを使用した学習

## 事実
- AI市場は2025年までに1000億ドルに達する (信頼度: 0.90)

## プロセス
### 機械学習の実装手順
一般的な機械学習プロジェクトの流れ
1. 問題を明確に定義する
2. データを収集・準備する
3. モデルを選択し訓練する
4. 結果を評価し改善する

## 洞察
- **future_trends** (high): AIは人間の能力を補完し、創造的な仕事に集中できる

## アクションアイテム
- [medium] AIツールを試してみる
  - 実践的な理解を深めるため
```

### CSV Format (for Relationships)

```csv
Subject,Predicate,Object,Confidence,Source Text
機械学習,is_a,人工知能,0.90,"機械学習は人工知能の一種である。"
深層学習,is_a,機械学習,0.85,"深層学習は機械学習の一種である。"
AI,causes,自動化,0.80,"AIによって多くの作業が自動化される。"
```

## Entity Types (Phase 4-3)

- **person**: 人物名 (Andrew Ng, etc.)
- **organization**: 組織名 (Google, Stanford, etc.)
- **location**: 地名 (東京, アメリカ, etc.)
- **date**: 日付 (2025年, etc.)
- **time**: 時刻
- **technical_term**: 専門用語 (機械学習, AI, etc.)
- **metric**: 数値・統計 (1000億ドル, 95%, etc.)
- **concept**: 概念
- **other**: その他

## Relationship Types (Phase 4-4)

- **is_a**: AはBの一種 (Machine Learning IS_A Artificial Intelligence)
- **part_of**: AはBの一部 (GPU PART_OF Computer)
- **causes**: AによってBが起こる (AI CAUSES Automation)
- **precedes**: AはBの前に起こる (Training PRECEDES Deployment)
- **similar_to**: AはBに類似 (ML SIMILAR_TO Deep Learning)
- **related_to**: AはBに関連 (AI RELATED_TO Data Science)
- **contains**: AはBを含む (AI CONTAINS Machine Learning)
- **opposite_of**: AはBの反対 (Supervised OPPOSITE_OF Unsupervised)

## Japanese Language Support

The system provides comprehensive Japanese language support:

- **Tokenization**: Japanese-aware text splitting
- **Entity Recognition**: Recognizes Japanese names, organizations, terms
  - 人名: 松本太郎、田中花子
  - 組織名: トヨタ自動車、東京大学
  - 専門用語: 機械学習、深層学習、ニューラルネットワーク
  - カタカナ語: データサイエンス、アルゴリズム

- **Relationship Extraction**: Handles Japanese grammar patterns
  - 「AはBである」→ IS_A
  - 「AによってBが起こる」→ CAUSES
  - 「AはBを含む」→ CONTAINS

- **Output**: Full Unicode support in YAML/JSON/Markdown

## Database Schema

The Knowledge model stores extracted knowledge:

```sql
CREATE TABLE knowledge (
    id SERIAL PRIMARY KEY,
    book_title VARCHAR(255) NOT NULL,
    format VARCHAR(10) NOT NULL,  -- 'yaml', 'json', 'markdown'
    score FLOAT,                   -- Quality score (0.0-1.0)
    yaml_text TEXT NOT NULL,       -- Structured content as text
    content_blob BYTEA,            -- Binary content
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_knowledge_book_title ON knowledge(book_title);
CREATE INDEX idx_knowledge_format ON knowledge(format);
CREATE INDEX idx_knowledge_score ON knowledge(score);
```

## Quality Scoring

Quality score (0.0-1.0) is calculated based on:

- **Main Topics** (15%): Presence of identified topics
- **Concepts** (25%): Number and quality of concept definitions
- **Facts** (15%): Extracted factual statements
- **Processes** (10%): Identified procedures
- **Insights** (20%): Key takeaways
- **Action Items** (15%): Actionable recommendations

## Advanced Features

### 1. Incremental Extraction
- Add to existing knowledge base
- Merge multiple sources

### 2. Duplicate Detection
- Entity deduplication
- Relationship deduplication

### 3. Citation Tracking
- Page numbers
- Source text preservation

### 4. Chunking for Long Documents
- Automatic text splitting
- Overlap for context preservation
- Merge results from multiple chunks

### 5. Mock Mode
- Works without API keys
- Generates sample data for testing
- Useful for development

## Testing

Run the comprehensive test suite:

```bash
# Run all tests
python test_knowledge.py

# Run specific test categories
pytest test_knowledge.py::test_knowledge_service_basic
pytest test_knowledge.py::test_entity_extraction
pytest test_knowledge.py::test_relationship_extraction
pytest test_knowledge.py::test_knowledge_graph
```

## Configuration

Set environment variables in `.env`:

```bash
# LLM API Keys (at least one required for production)
ANTHROPIC_API_KEY=your_anthropic_key
OPENAI_API_KEY=your_openai_key

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/kindle_ocr
```

## Performance

- **Knowledge Extraction**: 5-10s for typical book chapter (~3000 chars)
- **Entity Extraction**: 2-5s for typical text
- **Relationship Extraction**: 3-7s for typical text
- **Knowledge Graph**: 5-10s (includes entity + relationship extraction)

Performance varies based on:
- Text length
- Language complexity
- LLM API response time
- Number of entities/relationships

## Error Handling

The service includes comprehensive error handling:

- Invalid input validation
- LLM API failures with retry logic
- Database connection issues
- Malformed JSON/YAML output
- Empty or missing text

## Future Enhancements

- Support for additional languages (Chinese, Korean, etc.)
- Advanced graph algorithms (centrality, communities)
- Integration with graph databases (Neo4j, etc.)
- Real-time streaming extraction
- Interactive knowledge refinement
- Multi-document knowledge merging
- Temporal knowledge tracking

## Integration with Other Phases

Phase 4 integrates with:

- **Phase 1 (OCR)**: Extracts knowledge from OCR results
- **Phase 2 (RAG)**: Provides structured knowledge for retrieval
- **Phase 3 (Summary)**: Complements summarization with structured extraction
- **Future Phases**: Foundation for advanced analytics and insights

## License

Part of the Kindle OCR MVP project.

## Support

For issues or questions, refer to the main project documentation.
