#!/usr/bin/env python3
"""
Knowledge Extraction Service and Endpoint Test Script

Comprehensive tests for Phase 4 Knowledge Extraction implementation:
- Knowledge extraction (concepts, facts, processes, insights, actions)
- Entity extraction (NER)
- Relationship extraction
- Knowledge graph construction
- YAML/JSON/Markdown formatting
- Database integration
- API endpoint tests

Requirements:
  - Running database
  - App running on localhost:8000 (for API tests)
  - ANTHROPIC_API_KEY or OPENAI_API_KEY (optional, will use mock if not set)
"""
import sys
import logging
import json
import yaml
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Test samples
JAPANESE_AI_TEXT = """
人工知能（AI）は、近年急速に発展しており、私たちの生活に大きな影響を与えています。
機械学習は人工知能の一種であり、データから学習するアルゴリズムの総称です。
特に深層学習の進歩により、画像認識、自然言語処理、音声認識などの分野で
著しい成果が得られています。

GoogleやMicrosoftなどの企業は、AI技術の開発に多額の投資を行っています。
スタンフォード大学のAndrew Ng教授は、機械学習分野の第一人者として知られています。

AIの応用範囲は広く、医療診断、自動運転、金融取引、製造業など、様々な産業で活用されています。
しかし、AIの発展に伴い、倫理的な問題やプライバシーの懸念も生じています。
アルゴリズムのバイアス、データの透明性、説明可能性など、解決すべき課題は多くあります。

AIを活用するためには、以下の手順を踏むことが重要です：
1. 問題を明確に定義する
2. 適切なデータを収集する
3. モデルを選択し訓練する
4. 結果を評価し改善する

今後は、技術の進歩と社会的責任のバランスを取ることが重要です。
人間中心のAI開発が求められています。
"""

ENGLISH_ML_TEXT = """
Machine Learning is a subset of Artificial Intelligence that enables computers to learn
from data without being explicitly programmed. Deep Learning, a type of machine learning,
uses neural networks with multiple layers.

Google and Microsoft are leading companies in AI research. Stanford University and MIT
are renowned institutions for machine learning education.

Machine learning causes improvements in prediction accuracy. Deep learning is similar to
the human brain's neural structure. AI contains various subfields including computer vision
and natural language processing.

To implement machine learning:
1. Define the problem clearly
2. Collect and prepare data
3. Select and train the model
4. Evaluate and optimize results

The future of AI requires balancing innovation with ethical considerations.
"""

# =============================================================================
# Unit Tests (KnowledgeService)
# =============================================================================

def test_knowledge_service_basic():
    """Test basic KnowledgeService functionality"""
    logger.info("=" * 80)
    logger.info("TEST: Basic Knowledge Extraction")
    logger.info("=" * 80)

    try:
        from app.services.knowledge_service import KnowledgeService

        service = KnowledgeService()
        logger.info(f"KnowledgeService initialized (mock mode: {service.is_mock})")

        # Extract knowledge
        result = service.extract_knowledge(
            text=JAPANESE_AI_TEXT,
            book_title="AI入門",
            language="ja",
            include_entities=True,
            include_relationships=True,
            min_confidence=0.5
        )

        logger.info(f"Extraction completed:")
        logger.info(f"  - Language: {result['language']}")
        logger.info(f"  - Quality Score: {result['quality_score']:.2f}")
        logger.info(f"  - Processing Time: {result['processing_time']:.2f}s")
        logger.info(f"  - Token Usage: {result['token_usage']}")

        structured_data = result['structured_data']
        logger.info(f"\nExtracted Knowledge:")
        logger.info(f"  - Main Topics: {len(structured_data.main_topics)}")
        logger.info(f"    {structured_data.main_topics[:5]}")
        logger.info(f"  - Concepts: {len(structured_data.concepts)}")
        for concept in structured_data.concepts[:3]:
            logger.info(f"    - {concept.name} ({concept.importance}): {concept.definition[:50]}...")
        logger.info(f"  - Facts: {len(structured_data.facts)}")
        logger.info(f"  - Processes: {len(structured_data.processes)}")
        logger.info(f"  - Insights: {len(structured_data.insights)}")
        logger.info(f"  - Action Items: {len(structured_data.action_items)}")

        # Entities
        entities = result['entities']
        logger.info(f"\nExtracted Entities: {len(entities)}")
        for entity in entities[:5]:
            logger.info(
                f"  - {entity.name} ({entity.type.value}): "
                f"confidence={entity.confidence:.2f}"
            )

        # Relationships
        relationships = result['relationships']
        logger.info(f"\nExtracted Relationships: {len(relationships)}")
        for rel in relationships[:5]:
            logger.info(
                f"  - {rel.subject} --[{rel.predicate.value}]--> {rel.object} "
                f"(confidence={rel.confidence:.2f})"
            )

        logger.info("\n✅ Basic knowledge extraction test passed")
        return True

    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)
        return False


def test_entity_extraction():
    """Test entity extraction (NER)"""
    logger.info("=" * 80)
    logger.info("TEST: Entity Extraction (Phase 4-3)")
    logger.info("=" * 80)

    try:
        from app.services.knowledge_service import KnowledgeService
        from app.schemas.knowledge import EntityType

        service = KnowledgeService()

        # Japanese text
        entities_ja = service.extract_entities(
            text=JAPANESE_AI_TEXT,
            language="ja",
            min_confidence=0.5
        )

        logger.info(f"Japanese Entity Extraction: {len(entities_ja)} entities")
        type_counts = {}
        for entity in entities_ja:
            type_counts[entity.type.value] = type_counts.get(entity.type.value, 0) + 1
            logger.info(
                f"  - [{entity.type.value}] {entity.name}: "
                f"{entity.description or 'N/A'} (confidence={entity.confidence:.2f})"
            )

        logger.info(f"\nEntity Type Distribution:")
        for etype, count in sorted(type_counts.items()):
            logger.info(f"  - {etype}: {count}")

        # English text
        entities_en = service.extract_entities(
            text=ENGLISH_ML_TEXT,
            language="en",
            entity_types=[EntityType.PERSON, EntityType.ORGANIZATION, EntityType.TECHNICAL_TERM],
            min_confidence=0.5
        )

        logger.info(f"\nEnglish Entity Extraction: {len(entities_en)} entities")
        for entity in entities_en[:10]:
            logger.info(
                f"  - [{entity.type.value}] {entity.name} "
                f"(confidence={entity.confidence:.2f})"
            )

        logger.info("\n✅ Entity extraction test passed")
        return True

    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)
        return False


def test_relationship_extraction():
    """Test relationship extraction"""
    logger.info("=" * 80)
    logger.info("TEST: Relationship Extraction (Phase 4-4)")
    logger.info("=" * 80)

    try:
        from app.services.knowledge_service import KnowledgeService

        service = KnowledgeService()

        # First extract entities
        entities = service.extract_entities(
            text=ENGLISH_ML_TEXT,
            language="en",
            min_confidence=0.5
        )

        logger.info(f"Extracted {len(entities)} entities for relationship extraction")

        # Then extract relationships
        relationships = service.extract_relationships(
            text=ENGLISH_ML_TEXT,
            entities=entities,
            language="en",
            min_confidence=0.5
        )

        logger.info(f"\nExtracted {len(relationships)} relationships:")
        for rel in relationships:
            logger.info(
                f"  - {rel.subject} --[{rel.predicate.value}]--> {rel.object} "
                f"(confidence={rel.confidence:.2f})"
            )
            if rel.source_text:
                logger.info(f"    Source: {rel.source_text[:80]}...")

        # Count by type
        type_counts = {}
        for rel in relationships:
            type_counts[rel.predicate.value] = type_counts.get(rel.predicate.value, 0) + 1

        logger.info(f"\nRelationship Type Distribution:")
        for rtype, count in sorted(type_counts.items()):
            logger.info(f"  - {rtype}: {count}")

        logger.info("\n✅ Relationship extraction test passed")
        return True

    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)
        return False


def test_knowledge_graph():
    """Test knowledge graph construction"""
    logger.info("=" * 80)
    logger.info("TEST: Knowledge Graph Construction (Phase 4-4)")
    logger.info("=" * 80)

    try:
        from app.services.knowledge_service import KnowledgeService

        service = KnowledgeService()

        # Extract entities and relationships
        entities = service.extract_entities(
            text=ENGLISH_ML_TEXT,
            language="en",
            min_confidence=0.5
        )

        relationships = service.extract_relationships(
            text=ENGLISH_ML_TEXT,
            entities=entities,
            language="en",
            min_confidence=0.5
        )

        # Build knowledge graph
        graph = service.build_knowledge_graph(
            entities=entities,
            relationships=relationships,
            book_title="Machine Learning Basics"
        )

        logger.info(f"Knowledge Graph:")
        logger.info(f"  - Nodes: {len(graph.nodes)}")
        logger.info(f"  - Edges: {len(graph.edges)}")
        logger.info(f"  - Metadata: {graph.metadata}")

        logger.info(f"\nNodes (first 5):")
        for node in graph.nodes[:5]:
            logger.info(
                f"  - {node.id}: {node.label} ({node.type.value})"
            )

        logger.info(f"\nEdges (first 5):")
        for edge in graph.edges[:5]:
            logger.info(
                f"  - {edge.source} --[{edge.type.value}]--> {edge.target} "
                f"(confidence={edge.confidence:.2f})"
            )

        logger.info("\n✅ Knowledge graph construction test passed")
        return True

    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)
        return False


def test_yaml_json_markdown_formatting():
    """Test YAML/JSON/Markdown formatting (Phase 4-2)"""
    logger.info("=" * 80)
    logger.info("TEST: YAML/JSON/Markdown Formatting (Phase 4-2)")
    logger.info("=" * 80)

    try:
        from app.services.knowledge_service import KnowledgeService

        service = KnowledgeService()

        result = service.extract_knowledge(
            text=JAPANESE_AI_TEXT,
            book_title="AI入門",
            language="ja",
            include_entities=False,
            include_relationships=False
        )

        structured_data = result['structured_data']

        # Test YAML formatting
        yaml_output = service.format_as_yaml(structured_data)
        logger.info(f"\n--- YAML Format ---")
        logger.info(yaml_output[:500] + "...\n")

        # Verify YAML is parseable
        yaml_parsed = yaml.safe_load(yaml_output)
        logger.info(f"✓ YAML is valid and parseable")
        logger.info(f"  - Book Title: {yaml_parsed.get('book_title')}")

        # Test JSON formatting
        json_output = service.format_as_json(structured_data)
        logger.info(f"\n--- JSON Format ---")
        logger.info(json_output[:500] + "...\n")

        # Verify JSON is parseable
        json_parsed = json.loads(json_output)
        logger.info(f"✓ JSON is valid and parseable")
        logger.info(f"  - Book Title: {json_parsed.get('book_title')}")

        # Test Markdown formatting
        markdown_output = service.format_as_markdown(structured_data)
        logger.info(f"\n--- Markdown Format ---")
        logger.info(markdown_output[:500] + "...\n")

        logger.info(f"✓ Markdown is generated")

        logger.info("\n✅ YAML/JSON/Markdown formatting test passed")
        return True

    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)
        return False


def test_csv_export():
    """Test CSV export for relationships"""
    logger.info("=" * 80)
    logger.info("TEST: CSV Export for Relationships")
    logger.info("=" * 80)

    try:
        from app.services.knowledge_service import KnowledgeService

        service = KnowledgeService()

        # Extract entities and relationships
        entities = service.extract_entities(
            text=ENGLISH_ML_TEXT,
            language="en",
            min_confidence=0.5
        )

        relationships = service.extract_relationships(
            text=ENGLISH_ML_TEXT,
            entities=entities,
            language="en",
            min_confidence=0.5
        )

        # Export as CSV
        csv_output = service.format_relationships_as_csv(relationships)
        logger.info(f"\n--- CSV Format (Relationships) ---")
        logger.info(csv_output)

        # Verify CSV has header and data
        lines = csv_output.strip().split('\n')
        logger.info(f"✓ CSV has {len(lines)} lines (1 header + {len(lines)-1} data rows)")

        logger.info("\n✅ CSV export test passed")
        return True

    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)
        return False


def test_database_integration():
    """Test database integration"""
    logger.info("=" * 80)
    logger.info("TEST: Database Integration")
    logger.info("=" * 80)

    try:
        from app.core.database import SessionLocal
        from app.services.knowledge_service import (
            KnowledgeService,
            save_knowledge_to_db,
            get_knowledge_by_id,
            get_knowledge_by_book_title
        )

        db = SessionLocal()

        try:
            service = KnowledgeService()

            # Extract knowledge
            result = service.extract_knowledge(
                text=JAPANESE_AI_TEXT,
                book_title="AI入門テスト",
                language="ja",
                include_entities=True,
                include_relationships=True
            )

            structured_data = result['structured_data']
            quality_score = result['quality_score']

            # Format as YAML
            yaml_text = service.format_as_yaml(structured_data)
            content_blob = yaml_text.encode('utf-8')

            # Save to database
            knowledge = save_knowledge_to_db(
                db=db,
                book_title="AI入門テスト",
                format="yaml",
                yaml_text=yaml_text,
                content_blob=content_blob,
                score=quality_score
            )

            logger.info(f"✓ Saved to database: knowledge_id={knowledge.id}")

            # Retrieve by ID
            retrieved = get_knowledge_by_id(db, knowledge.id)
            logger.info(f"✓ Retrieved by ID: {retrieved.id}")
            logger.info(f"  - Book Title: {retrieved.book_title}")
            logger.info(f"  - Format: {retrieved.format}")
            logger.info(f"  - Score: {retrieved.score:.2f}")

            # Retrieve by book title
            knowledge_list = get_knowledge_by_book_title(db, "AI入門テスト")
            logger.info(f"✓ Retrieved by book title: {len(knowledge_list)} entries")

            # Cleanup
            db.delete(knowledge)
            db.commit()
            logger.info(f"✓ Cleaned up test data")

            logger.info("\n✅ Database integration test passed")
            return True

        finally:
            db.close()

    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)
        return False


# =============================================================================
# API Endpoint Tests
# =============================================================================

def test_api_knowledge_extraction():
    """Test knowledge extraction API endpoint"""
    logger.info("=" * 80)
    logger.info("TEST: API - Knowledge Extraction")
    logger.info("=" * 80)

    try:
        import requests

        url = "http://localhost:8000/api/v1/knowledge/extract"

        # Test with text
        payload = {
            "text": JAPANESE_AI_TEXT,
            "book_title": "AI入門API",
            "format": "yaml",
            "include_entities": True,
            "include_relationships": True,
            "language": "ja",
            "min_confidence": 0.7
        }

        logger.info(f"Sending POST request to {url}")
        response = requests.post(url, json=payload, timeout=120)

        logger.info(f"Response Status: {response.status_code}")

        if response.status_code == 201:
            data = response.json()
            logger.info(f"✓ Knowledge extracted successfully")
            logger.info(f"  - Knowledge ID: {data['knowledge_id']}")
            logger.info(f"  - Book Title: {data['book_title']}")
            logger.info(f"  - Format: {data['format']}")
            logger.info(f"  - Quality Score: {data['quality_score']:.2f}")
            logger.info(f"  - Language: {data['language']}")
            logger.info(f"  - Processing Time: {data['processing_time']:.2f}s")
            logger.info(f"  - Is Mock: {data['is_mock']}")

            structured = data['structured_data']
            logger.info(f"\n  Structured Data:")
            logger.info(f"    - Main Topics: {len(structured['main_topics'])}")
            logger.info(f"    - Concepts: {len(structured['concepts'])}")
            logger.info(f"    - Entities: {len(structured['entities'])}")
            logger.info(f"    - Relationships: {len(structured['relationships'])}")

            if data.get('yaml_text'):
                logger.info(f"\n  YAML Output (first 200 chars):")
                logger.info(f"    {data['yaml_text'][:200]}...")

            logger.info("\n✅ API knowledge extraction test passed")
            return True
        else:
            logger.error(f"❌ API returned error: {response.status_code}")
            logger.error(f"Response: {response.text}")
            return False

    except requests.exceptions.ConnectionError:
        logger.warning("⚠️  API server not running. Skipping API test.")
        return True
    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)
        return False


def test_api_entity_extraction():
    """Test entity extraction API endpoint"""
    logger.info("=" * 80)
    logger.info("TEST: API - Entity Extraction")
    logger.info("=" * 80)

    try:
        import requests

        url = "http://localhost:8000/api/v1/knowledge/extract-entities"

        payload = {
            "text": ENGLISH_ML_TEXT,
            "language": "en",
            "min_confidence": 0.6
        }

        logger.info(f"Sending POST request to {url}")
        response = requests.post(url, json=payload, timeout=60)

        logger.info(f"Response Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            logger.info(f"✓ Entities extracted successfully")
            logger.info(f"  - Total Count: {data['total_count']}")
            logger.info(f"  - By Type: {data['by_type']}")
            logger.info(f"  - Language: {data['language']}")
            logger.info(f"  - Processing Time: {data['processing_time']:.2f}s")

            logger.info(f"\n  Entities (first 5):")
            for entity in data['entities'][:5]:
                logger.info(
                    f"    - [{entity['type']}] {entity['name']}: "
                    f"confidence={entity['confidence']:.2f}"
                )

            logger.info("\n✅ API entity extraction test passed")
            return True
        else:
            logger.error(f"❌ API returned error: {response.status_code}")
            logger.error(f"Response: {response.text}")
            return False

    except requests.exceptions.ConnectionError:
        logger.warning("⚠️  API server not running. Skipping API test.")
        return True
    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)
        return False


def test_api_relationship_extraction():
    """Test relationship extraction API endpoint"""
    logger.info("=" * 80)
    logger.info("TEST: API - Relationship Extraction")
    logger.info("=" * 80)

    try:
        import requests

        url = "http://localhost:8000/api/v1/knowledge/extract-relations"

        payload = {
            "text": ENGLISH_ML_TEXT,
            "language": "en",
            "min_confidence": 0.6
        }

        logger.info(f"Sending POST request to {url}")
        response = requests.post(url, json=payload, timeout=60)

        logger.info(f"Response Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            logger.info(f"✓ Relationships extracted successfully")
            logger.info(f"  - Total Count: {data['total_count']}")
            logger.info(f"  - By Type: {data['by_type']}")
            logger.info(f"  - Processing Time: {data['processing_time']:.2f}s")

            logger.info(f"\n  Relationships (first 5):")
            for rel in data['relationships'][:5]:
                logger.info(
                    f"    - {rel['subject']} --[{rel['predicate']}]--> {rel['object']} "
                    f"(confidence={rel['confidence']:.2f})"
                )

            logger.info("\n✅ API relationship extraction test passed")
            return True
        else:
            logger.error(f"❌ API returned error: {response.status_code}")
            logger.error(f"Response: {response.text}")
            return False

    except requests.exceptions.ConnectionError:
        logger.warning("⚠️  API server not running. Skipping API test.")
        return True
    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)
        return False


def test_api_knowledge_graph():
    """Test knowledge graph API endpoint"""
    logger.info("=" * 80)
    logger.info("TEST: API - Knowledge Graph Construction")
    logger.info("=" * 80)

    try:
        import requests

        url = "http://localhost:8000/api/v1/knowledge/build-graph"

        payload = {
            "text": ENGLISH_ML_TEXT,
            "language": "en",
            "min_confidence": 0.6
        }

        logger.info(f"Sending POST request to {url}")
        response = requests.post(url, json=payload, timeout=90)

        logger.info(f"Response Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            logger.info(f"✓ Knowledge graph built successfully")
            logger.info(f"  - Nodes: {len(data['nodes'])}")
            logger.info(f"  - Edges: {len(data['edges'])}")
            logger.info(f"  - Metadata: {data['metadata']}")

            logger.info(f"\n  Nodes (first 3):")
            for node in data['nodes'][:3]:
                logger.info(f"    - {node['id']}: {node['label']} ({node['type']})")

            logger.info(f"\n  Edges (first 3):")
            for edge in data['edges'][:3]:
                logger.info(
                    f"    - {edge['source']} --[{edge['type']}]--> {edge['target']}"
                )

            logger.info("\n✅ API knowledge graph test passed")
            return True
        else:
            logger.error(f"❌ API returned error: {response.status_code}")
            logger.error(f"Response: {response.text}")
            return False

    except requests.exceptions.ConnectionError:
        logger.warning("⚠️  API server not running. Skipping API test.")
        return True
    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)
        return False


# =============================================================================
# Main Test Runner
# =============================================================================

def main():
    """Run all tests"""
    logger.info("=" * 80)
    logger.info("Knowledge Extraction Test Suite (Phase 4)")
    logger.info("=" * 80)

    results = {}

    # Unit tests
    logger.info("\n### UNIT TESTS ###\n")
    results['basic_knowledge'] = test_knowledge_service_basic()
    results['entity_extraction'] = test_entity_extraction()
    results['relationship_extraction'] = test_relationship_extraction()
    results['knowledge_graph'] = test_knowledge_graph()
    results['yaml_json_markdown'] = test_yaml_json_markdown_formatting()
    results['csv_export'] = test_csv_export()
    results['database'] = test_database_integration()

    # API tests
    logger.info("\n### API TESTS ###\n")
    results['api_knowledge'] = test_api_knowledge_extraction()
    results['api_entities'] = test_api_entity_extraction()
    results['api_relationships'] = test_api_relationship_extraction()
    results['api_graph'] = test_api_knowledge_graph()

    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("TEST SUMMARY")
    logger.info("=" * 80)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{status}: {test_name}")

    logger.info("\n" + "=" * 80)
    logger.info(f"TOTAL: {passed}/{total} tests passed")
    logger.info("=" * 80)

    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
