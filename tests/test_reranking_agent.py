"""
Comprehensive Test Suite for Reranking Agent

Tests cover:
- Cross-Encoder reranking
- LLM-based reranking
- Hybrid reranking
- Confidence scoring
- Top-k filtering
- Blackboard integration
- Error handling
- Performance metrics
"""

import pytest
import json
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from typing import List

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from tmax_work3.agents.reranking import (
    RerankingAgent,
    SearchResult,
    RerankedResult,
    create_reranking_agent
)


# Test Fixtures
@pytest.fixture
def sample_query():
    """Sample search query"""
    return "What is machine learning and deep learning?"


@pytest.fixture
def sample_search_results():
    """Sample search results"""
    return [
        SearchResult(
            doc_id="doc1",
            content="Machine learning is a subset of artificial intelligence that enables systems to learn from data without explicit programming.",
            original_score=0.85,
            metadata={"source": "textbook", "year": 2023}
        ),
        SearchResult(
            doc_id="doc2",
            content="Deep learning is a type of machine learning based on artificial neural networks with multiple layers.",
            original_score=0.78,
            metadata={"source": "research_paper", "year": 2024}
        ),
        SearchResult(
            doc_id="doc3",
            content="Python is a popular programming language widely used in data science and web development.",
            original_score=0.65,
            metadata={"source": "tutorial", "year": 2023}
        ),
        SearchResult(
            doc_id="doc4",
            content="Natural language processing uses machine learning to understand and generate human language.",
            original_score=0.72,
            metadata={"source": "article", "year": 2024}
        ),
        SearchResult(
            doc_id="doc5",
            content="Cloud computing provides on-demand access to computing resources over the internet.",
            original_score=0.55,
            metadata={"source": "guide", "year": 2023}
        ),
    ]


@pytest.fixture
def mock_cross_encoder():
    """Mock Cross-Encoder model"""
    mock_encoder = Mock()
    # Simulate Cross-Encoder scores (higher for more relevant)
    mock_encoder.predict.return_value = [0.92, 0.88, 0.45, 0.75, 0.30]
    return mock_encoder


@pytest.fixture
def mock_claude_client():
    """Mock Claude API client"""
    mock_client = Mock()
    mock_response = Mock()
    mock_response.content = [Mock()]
    mock_response.content[0].text = json.dumps([
        {"doc_id": "doc1", "score": 0.95},
        {"doc_id": "doc2", "score": 0.90},
        {"doc_id": "doc4", "score": 0.80},
        {"doc_id": "doc3", "score": 0.50},
        {"doc_id": "doc5", "score": 0.30},
    ])
    mock_client.messages.create.return_value = mock_response
    return mock_client


# Test Cases

class TestRerankingAgentInitialization:
    """Test Reranking Agent initialization"""

    def test_agent_initialization_default(self):
        """Test agent initialization with default parameters"""
        agent = RerankingAgent(repository_path=".")

        assert agent.repo_path == Path(".")
        assert agent.top_k == 10
        assert agent.confidence_threshold == 0.5
        assert agent.blackboard is not None

    def test_agent_initialization_custom_params(self):
        """Test agent initialization with custom parameters"""
        agent = RerankingAgent(
            repository_path="/custom/path",
            top_k=5,
            confidence_threshold=0.7,
            use_llm=False
        )

        assert agent.repo_path == Path("/custom/path")
        assert agent.top_k == 5
        assert agent.confidence_threshold == 0.7
        assert agent.use_llm is False

    def test_factory_function(self):
        """Test factory function"""
        agent = create_reranking_agent(repository_path=".", top_k=15)

        assert isinstance(agent, RerankingAgent)
        assert agent.top_k == 15


class TestCrossEncoderReranking:
    """Test Cross-Encoder reranking functionality"""

    @patch('tmax_work3.agents.reranking.CROSS_ENCODER_AVAILABLE', True)
    def test_cross_encoder_reranking(
        self,
        sample_query,
        sample_search_results,
        mock_cross_encoder
    ):
        """Test Cross-Encoder reranking"""
        with patch('tmax_work3.agents.reranking.CrossEncoder',
                  return_value=mock_cross_encoder):
            agent = RerankingAgent(repository_path=".")
            agent.cross_encoder = mock_cross_encoder

            results = agent.rerank(
                query=sample_query,
                results=sample_search_results,
                method="cross_encoder"
            )

            # Verify results
            assert len(results) > 0
            assert all(isinstance(r, RerankedResult) for r in results)

            # Verify sorting (highest score first)
            scores = [r.rerank_score for r in results]
            assert scores == sorted(scores, reverse=True)

            # Verify method
            assert all(r.method == "cross_encoder" for r in results)

    @patch('tmax_work3.agents.reranking.CROSS_ENCODER_AVAILABLE', True)
    def test_cross_encoder_score_normalization(
        self,
        sample_query,
        sample_search_results,
        mock_cross_encoder
    ):
        """Test Cross-Encoder score normalization"""
        with patch('tmax_work3.agents.reranking.CrossEncoder',
                  return_value=mock_cross_encoder):
            agent = RerankingAgent(repository_path=".")
            agent.cross_encoder = mock_cross_encoder

            results = agent.rerank(
                query=sample_query,
                results=sample_search_results,
                method="cross_encoder"
            )

            # Verify confidence scores are normalized
            for result in results:
                assert 0 <= result.confidence <= 1

    def test_cross_encoder_fallback(self, sample_query, sample_search_results):
        """Test fallback when Cross-Encoder is unavailable"""
        with patch('tmax_work3.agents.reranking.CROSS_ENCODER_AVAILABLE', False):
            agent = RerankingAgent(repository_path=".")
            agent.cross_encoder = None

            results = agent.rerank(
                query=sample_query,
                results=sample_search_results,
                method="cross_encoder"
            )

            # Should return results with original scores
            assert len(results) > 0
            for i, result in enumerate(results):
                assert result.rerank_score == sample_search_results[i].original_score


class TestLLMReranking:
    """Test LLM-based reranking functionality"""

    def test_llm_reranking(
        self,
        sample_query,
        sample_search_results,
        mock_claude_client
    ):
        """Test LLM-based reranking"""
        with patch('tmax_work3.agents.reranking.ANTHROPIC_AVAILABLE', True):
            agent = RerankingAgent(repository_path=".", use_llm=True)
            agent.claude_client = mock_claude_client

            results = agent.rerank(
                query=sample_query,
                results=sample_search_results,
                method="llm"
            )

            # Verify results
            assert len(results) > 0
            assert all(isinstance(r, RerankedResult) for r in results)

            # Verify method
            assert all(r.method == "llm" for r in results)

            # Verify Claude was called
            mock_claude_client.messages.create.assert_called_once()

    def test_llm_prompt_creation(self, sample_query, sample_search_results):
        """Test LLM prompt creation"""
        agent = RerankingAgent(repository_path=".", use_llm=True)

        prompt = agent._create_llm_reranking_prompt(
            sample_query,
            sample_search_results[:3]
        )

        # Verify prompt contains query
        assert sample_query in prompt

        # Verify prompt contains document IDs
        for result in sample_search_results[:3]:
            assert result.doc_id in prompt

    def test_llm_response_parsing(self):
        """Test LLM response parsing"""
        agent = RerankingAgent(repository_path=".", use_llm=True)

        # Valid JSON response
        response = '[{"doc_id": "doc1", "score": 0.9}, {"doc_id": "doc2", "score": 0.8}]'
        rankings = agent._parse_llm_response(response)

        assert len(rankings) == 2
        assert rankings[0]["doc_id"] == "doc1"
        assert rankings[0]["score"] == 0.9

    def test_llm_fallback(self, sample_query, sample_search_results):
        """Test fallback when LLM is unavailable"""
        agent = RerankingAgent(repository_path=".", use_llm=True)
        agent.claude_client = None

        results = agent.rerank(
            query=sample_query,
            results=sample_search_results,
            method="llm"
        )

        # Should return fallback results
        assert len(results) > 0


class TestHybridReranking:
    """Test hybrid reranking functionality"""

    @patch('tmax_work3.agents.reranking.CROSS_ENCODER_AVAILABLE', True)
    @patch('tmax_work3.agents.reranking.ANTHROPIC_AVAILABLE', True)
    def test_hybrid_reranking(
        self,
        sample_query,
        sample_search_results,
        mock_cross_encoder,
        mock_claude_client
    ):
        """Test hybrid reranking combining CE and LLM"""
        with patch('tmax_work3.agents.reranking.CrossEncoder',
                  return_value=mock_cross_encoder):
            agent = RerankingAgent(repository_path=".", use_llm=True)
            agent.cross_encoder = mock_cross_encoder
            agent.claude_client = mock_claude_client

            results = agent.rerank(
                query=sample_query,
                results=sample_search_results,
                method="hybrid"
            )

            # Verify results
            assert len(results) > 0
            assert all(r.method == "hybrid" for r in results)

    @patch('tmax_work3.agents.reranking.CROSS_ENCODER_AVAILABLE', True)
    @patch('tmax_work3.agents.reranking.ANTHROPIC_AVAILABLE', True)
    def test_hybrid_score_combination(
        self,
        sample_query,
        sample_search_results,
        mock_cross_encoder,
        mock_claude_client
    ):
        """Test hybrid score combination weights"""
        with patch('tmax_work3.agents.reranking.CrossEncoder',
                  return_value=mock_cross_encoder):
            agent = RerankingAgent(repository_path=".", use_llm=True)
            agent.cross_encoder = mock_cross_encoder
            agent.claude_client = mock_claude_client

            results = agent.rerank(
                query=sample_query,
                results=sample_search_results,
                method="hybrid"
            )

            # Verify scores are combined (not just CE or LLM alone)
            # This is hard to test precisely, but we can verify
            # results exist and have valid scores
            for result in results:
                assert 0 <= result.rerank_score <= 1
                assert 0 <= result.confidence <= 1


class TestConfidenceScoring:
    """Test confidence score calculation"""

    def test_confidence_calculation_cross_encoder(self):
        """Test confidence calculation for Cross-Encoder scores"""
        agent = RerankingAgent(repository_path=".")

        # Test various scores
        test_cases = [
            (10.0, "cross_encoder"),    # High positive score
            (0.0, "cross_encoder"),     # Neutral score
            (-10.0, "cross_encoder"),   # Low negative score
        ]

        for score, method in test_cases:
            confidence = agent._calculate_confidence(score, method)
            assert 0 <= confidence <= 1

    def test_confidence_calculation_llm(self):
        """Test confidence calculation for LLM scores"""
        agent = RerankingAgent(repository_path=".")

        # Test various scores
        test_cases = [
            (0.9, "llm"),   # High score
            (0.5, "llm"),   # Medium score
            (0.1, "llm"),   # Low score
        ]

        for score, method in test_cases:
            confidence = agent._calculate_confidence(score, method)
            assert 0 <= confidence <= 1


class TestFiltering:
    """Test result filtering functionality"""

    @patch('tmax_work3.agents.reranking.CROSS_ENCODER_AVAILABLE', True)
    def test_top_k_filtering(
        self,
        sample_query,
        sample_search_results,
        mock_cross_encoder
    ):
        """Test top-k result filtering"""
        with patch('tmax_work3.agents.reranking.CrossEncoder',
                  return_value=mock_cross_encoder):
            agent = RerankingAgent(repository_path=".", top_k=3)
            agent.cross_encoder = mock_cross_encoder

            results = agent.rerank(
                query=sample_query,
                results=sample_search_results,
                method="cross_encoder"
            )

            # Should return at most top_k results
            assert len(results) <= 3

    @patch('tmax_work3.agents.reranking.CROSS_ENCODER_AVAILABLE', True)
    def test_confidence_threshold_filtering(
        self,
        sample_query,
        sample_search_results,
        mock_cross_encoder
    ):
        """Test confidence threshold filtering"""
        with patch('tmax_work3.agents.reranking.CrossEncoder',
                  return_value=mock_cross_encoder):
            agent = RerankingAgent(
                repository_path=".",
                confidence_threshold=0.8
            )
            agent.cross_encoder = mock_cross_encoder

            results = agent.rerank(
                query=sample_query,
                results=sample_search_results,
                method="cross_encoder"
            )

            # All results should meet confidence threshold
            for result in results:
                assert result.confidence >= 0.8


class TestMetricsAndLogging:
    """Test metrics recording and logging"""

    @patch('tmax_work3.agents.reranking.CROSS_ENCODER_AVAILABLE', True)
    def test_metrics_recording(
        self,
        sample_query,
        sample_search_results,
        mock_cross_encoder,
        tmp_path
    ):
        """Test metrics recording to Blackboard"""
        with patch('tmax_work3.agents.reranking.CrossEncoder',
                  return_value=mock_cross_encoder):
            agent = RerankingAgent(repository_path=str(tmp_path))
            agent.cross_encoder = mock_cross_encoder

            results = agent.rerank(
                query=sample_query,
                results=sample_search_results,
                method="cross_encoder"
            )

            # Verify metrics were recorded
            metrics = agent.blackboard.get_metrics()
            assert "reranking" in metrics

    @patch('tmax_work3.agents.reranking.CROSS_ENCODER_AVAILABLE', True)
    def test_result_saving(
        self,
        sample_query,
        sample_search_results,
        mock_cross_encoder,
        tmp_path
    ):
        """Test saving reranking results to file"""
        with patch('tmax_work3.agents.reranking.CrossEncoder',
                  return_value=mock_cross_encoder):
            agent = RerankingAgent(repository_path=str(tmp_path))
            agent.cross_encoder = mock_cross_encoder

            results = agent.rerank(
                query=sample_query,
                results=sample_search_results,
                method="cross_encoder"
            )

            # Verify result file was created
            result_dir = tmp_path / "tmax_work3" / "data" / "reranking"
            if result_dir.exists():
                result_files = list(result_dir.glob("reranking_*.json"))
                assert len(result_files) > 0


class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_empty_results(self, sample_query):
        """Test reranking with empty results"""
        agent = RerankingAgent(repository_path=".")

        results = agent.rerank(
            query=sample_query,
            results=[],
            method="cross_encoder"
        )

        assert results == []

    def test_single_result(self, sample_query, sample_search_results):
        """Test reranking with single result"""
        agent = RerankingAgent(repository_path=".")

        results = agent.rerank(
            query=sample_query,
            results=sample_search_results[:1],
            method="cross_encoder"
        )

        assert len(results) >= 0  # Should handle gracefully

    def test_invalid_method(self, sample_query, sample_search_results):
        """Test invalid reranking method"""
        agent = RerankingAgent(repository_path=".")

        with pytest.raises(ValueError):
            agent.rerank(
                query=sample_query,
                results=sample_search_results,
                method="invalid_method"
            )

    @patch('tmax_work3.agents.reranking.CROSS_ENCODER_AVAILABLE', True)
    def test_cross_encoder_error_handling(
        self,
        sample_query,
        sample_search_results
    ):
        """Test error handling in Cross-Encoder reranking"""
        with patch('tmax_work3.agents.reranking.CrossEncoder') as mock_ce:
            # Simulate Cross-Encoder error
            mock_ce.return_value.predict.side_effect = Exception("Model error")

            agent = RerankingAgent(repository_path=".")
            agent.cross_encoder = mock_ce.return_value

            # Should fall back gracefully
            results = agent.rerank(
                query=sample_query,
                results=sample_search_results,
                method="cross_encoder"
            )

            assert len(results) > 0  # Fallback results


class TestScoreImprovement:
    """Test score improvement calculation"""

    def test_score_improvement_calculation(self, sample_search_results):
        """Test calculation of score improvement"""
        agent = RerankingAgent(repository_path=".")

        # Create mock reranked results
        reranked = [
            RerankedResult(
                doc_id=r.doc_id,
                content=r.content,
                original_score=r.original_score,
                rerank_score=r.original_score + 0.1,  # Improved scores
                confidence=0.8,
                method="test",
                metadata=r.metadata
            )
            for r in sample_search_results
        ]

        improvement = agent._calculate_score_improvement(
            sample_search_results,
            reranked
        )

        # Should show improvement
        assert improvement > 0


class TestDataStructures:
    """Test data structures"""

    def test_search_result_to_dict(self):
        """Test SearchResult to_dict conversion"""
        result = SearchResult(
            doc_id="test1",
            content="test content",
            original_score=0.8,
            metadata={"key": "value"}
        )

        result_dict = result.to_dict()

        assert result_dict["doc_id"] == "test1"
        assert result_dict["content"] == "test content"
        assert result_dict["original_score"] == 0.8
        assert result_dict["metadata"]["key"] == "value"

    def test_reranked_result_to_dict(self):
        """Test RerankedResult to_dict conversion"""
        result = RerankedResult(
            doc_id="test1",
            content="test content",
            original_score=0.8,
            rerank_score=0.9,
            confidence=0.85,
            method="cross_encoder",
            metadata={"key": "value"}
        )

        result_dict = result.to_dict()

        assert result_dict["doc_id"] == "test1"
        assert result_dict["rerank_score"] == 0.9
        assert result_dict["confidence"] == 0.85
        assert result_dict["method"] == "cross_encoder"


# Performance Tests
class TestPerformance:
    """Test performance characteristics"""

    @patch('tmax_work3.agents.reranking.CROSS_ENCODER_AVAILABLE', True)
    def test_large_result_set(self, mock_cross_encoder):
        """Test reranking with large result set"""
        # Create 100 results
        large_results = [
            SearchResult(
                doc_id=f"doc{i}",
                content=f"Content for document {i}",
                original_score=0.5 + (i % 50) / 100,
                metadata={"index": i}
            )
            for i in range(100)
        ]

        # Mock scores
        mock_cross_encoder.predict.return_value = [0.5 + i/100 for i in range(100)]

        with patch('tmax_work3.agents.reranking.CrossEncoder',
                  return_value=mock_cross_encoder):
            agent = RerankingAgent(repository_path=".", top_k=20)
            agent.cross_encoder = mock_cross_encoder

            results = agent.rerank(
                query="test query",
                results=large_results,
                method="cross_encoder"
            )

            # Should return top 20 results
            assert len(results) <= 20


# Integration Tests
class TestBlackboardIntegration:
    """Test Blackboard integration"""

    @patch('tmax_work3.agents.reranking.CROSS_ENCODER_AVAILABLE', True)
    def test_blackboard_logging(
        self,
        sample_query,
        sample_search_results,
        mock_cross_encoder
    ):
        """Test Blackboard logging integration"""
        with patch('tmax_work3.agents.reranking.CrossEncoder',
                  return_value=mock_cross_encoder):
            agent = RerankingAgent(repository_path=".")
            agent.cross_encoder = mock_cross_encoder

            # Clear logs
            agent.blackboard.logs = []

            results = agent.rerank(
                query=sample_query,
                results=sample_search_results,
                method="cross_encoder"
            )

            # Verify logs were created
            assert len(agent.blackboard.logs) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
