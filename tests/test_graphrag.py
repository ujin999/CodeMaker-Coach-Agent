import pytest
from unittest.mock import MagicMock, patch
from packages.graphrag.driver import get_driver, close_driver
from packages.graphrag.sync import record_submission_to_graph
from packages.graphrag.query import get_user_weaknesses

def test_driver_offline_behavior():
    """Tests that the Neo4j driver raises or fails gracefully when offline settings are wrong,
    and fallback behaves correctly.
    """
    with patch("packages.graphrag.driver.GraphDatabase.driver") as mock_driver_cls:
        mock_driver_cls.side_effect = Exception("Connection refused")
        
        # Verify that get_driver raises exception when offline
        with pytest.raises(Exception) as exc_info:
            get_driver()
        assert "Connection refused" in str(exc_info.value)


def test_sync_to_graph_mocked():
    """Verifies that record_submission_to_graph runs correctly and sends correct Cypher parameters."""
    mock_session = MagicMock()
    mock_driver = MagicMock()
    mock_driver.session.return_value.__enter__.return_value = mock_session

    with patch("packages.graphrag.sync.get_driver", return_value=mock_driver):
        # 1. Test AC submission sync
        record_submission_to_graph(
            user_id=1,
            user_email="test@codemaker.io",
            problem_id="bfs_maze",
            problem_title="Maze Escape",
            problem_difficulty="medium",
            problem_algorithms=["bfs"],
            status="AC",
        )
        
        # Assert that session.run was called to perform Cypher update
        assert mock_session.run.call_count >= 1
        # Check first query parameters
        first_call_args = mock_session.run.call_args_list[0][1]
        assert first_call_args["user_id"] == 1
        assert first_call_args["problem_id"] == "bfs_maze"
        assert "bfs" in first_call_args["algorithms"]

        # Reset mock
        mock_session.reset_mock()

        # 2. Test WA submission sync
        record_submission_to_graph(
            user_id=1,
            user_email="test@codemaker.io",
            problem_id="bfs_maze",
            problem_title="Maze Escape",
            problem_difficulty="medium",
            problem_algorithms=["bfs"],
            status="WA",
        )
        assert mock_session.run.call_count >= 1
        wa_call_args = mock_session.run.call_args_list[0][1]
        assert wa_call_args["user_id"] == 1
        assert wa_call_args["problem_id"] == "bfs_maze"


def test_query_weaknesses_mocked():
    """Verifies that get_user_weaknesses queries Neo4j correctly and formats the output."""
    mock_session = MagicMock()
    mock_driver = MagicMock()
    mock_driver.session.return_value.__enter__.return_value = mock_session

    # Mock Neo4j query results
    mock_concept_record = MagicMock()
    mock_concept_record.__getitem__.side_effect = lambda key: {"concept": "bfs", "score": 6.5}[key]
    
    mock_error_record = MagicMock()
    mock_error_record.__getitem__.side_effect = lambda key: {"error_type": "WA", "err_count": 4}[key]

    mock_session.run.side_effect = [
        [mock_concept_record],  # First query result (concepts)
        [mock_error_record]     # Second query result (errors)
    ]

    with patch("packages.graphrag.query.get_driver", return_value=mock_driver):
        result = get_user_weaknesses(user_id=1)
        
        # Verify formatting
        assert len(result["weak_concepts"]) == 1
        assert result["weak_concepts"][0]["concept"] == "bfs"
        assert result["weak_concepts"][0]["score"] == 6.5
        
        assert len(result["top_errors"]) == 1
        assert result["top_errors"][0]["error_type"] == "WA"
        assert result["top_errors"][0]["count"] == 4
        
        assert "너비 우선 탐색 (BFS)" in result["recommendation"]
        assert "틀렸습니다 (Wrong Answer)" in result["recommendation"] or "오답 요인" in result["recommendation"]
