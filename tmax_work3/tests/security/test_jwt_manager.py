"""
Test cases for JWT Manager (A-JWT)
Zero-Trust認証システムのJWT管理テスト
"""
import pytest
import time
from datetime import datetime, timedelta
from pathlib import Path
import sys

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from tmax_work3.security.jwt_manager import JWTManager, TokenStore
from tmax_work3.blackboard.state_manager import AgentType


class TestJWTManager:
    """JWT Manager テストケース"""

    @pytest.fixture
    def jwt_manager(self, tmp_path):
        """JWTマネージャーのフィクスチャ"""
        token_store_path = tmp_path / "token_store.json"
        return JWTManager(
            secret_key="test-secret-key-12345",
            algorithm="HS256",
            token_expiry_hours=1,
            token_store_path=str(token_store_path)
        )

    def test_issue_token_success(self, jwt_manager):
        """トークン発行成功テスト"""
        token = jwt_manager.issue_token(
            agent_type=AgentType.BUILDER,
            permissions=["read", "write"],
            metadata={"worktree": "build_env"}
        )

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

    def test_verify_token_success(self, jwt_manager):
        """トークン検証成功テスト"""
        token = jwt_manager.issue_token(
            agent_type=AgentType.QA,
            permissions=["read", "execute"]
        )

        payload = jwt_manager.verify_token(token)

        assert payload is not None
        assert payload["agent_type"] == AgentType.QA.value
        assert "read" in payload["permissions"]
        assert "execute" in payload["permissions"]
        assert "exp" in payload
        assert "iat" in payload
        assert "jti" in payload  # JWT ID (nonce)

    def test_verify_invalid_token(self, jwt_manager):
        """無効なトークン検証テスト"""
        invalid_token = "invalid.token.here"

        payload = jwt_manager.verify_token(invalid_token)
        assert payload is None

    def test_verify_expired_token(self, jwt_manager):
        """期限切れトークン検証テスト"""
        # 期限切れトークンを作成（-1時間）
        jwt_manager_expired = JWTManager(
            secret_key="test-secret-key-12345",
            algorithm="HS256",
            token_expiry_hours=-1  # 即座に期限切れ
        )

        token = jwt_manager_expired.issue_token(
            agent_type=AgentType.DEPLOYER,
            permissions=["deploy"]
        )

        time.sleep(1)  # 1秒待機

        payload = jwt_manager_expired.verify_token(token)
        assert payload is None

    def test_revoke_token_success(self, jwt_manager):
        """トークン失効成功テスト"""
        token = jwt_manager.issue_token(
            agent_type=AgentType.SECURITY,
            permissions=["scan"]
        )

        # トークンを検証（有効）
        payload = jwt_manager.verify_token(token)
        assert payload is not None

        # トークンを失効
        jti = payload["jti"]
        result = jwt_manager.revoke_token(jti)
        assert result is True

        # 失効後のトークンを検証（無効）
        payload_after = jwt_manager.verify_token(token)
        assert payload_after is None

    def test_is_token_revoked(self, jwt_manager):
        """トークン失効状態確認テスト"""
        token = jwt_manager.issue_token(
            agent_type=AgentType.AUDIT,
            permissions=["audit"]
        )

        payload = jwt_manager.verify_token(token)
        jti = payload["jti"]

        # 失効前
        assert jwt_manager.is_token_revoked(jti) is False

        # 失効
        jwt_manager.revoke_token(jti)

        # 失効後
        assert jwt_manager.is_token_revoked(jti) is True

    def test_replay_attack_prevention(self, jwt_manager):
        """リプレイ攻撃防止テスト（nonce確認）"""
        token1 = jwt_manager.issue_token(
            agent_type=AgentType.BUILDER,
            permissions=["build"]
        )

        token2 = jwt_manager.issue_token(
            agent_type=AgentType.BUILDER,
            permissions=["build"]
        )

        payload1 = jwt_manager.verify_token(token1)
        payload2 = jwt_manager.verify_token(token2)

        # 異なるnonce（jti）を持つことを確認
        assert payload1["jti"] != payload2["jti"]

    def test_token_metadata(self, jwt_manager):
        """トークンメタデータテスト"""
        metadata = {
            "worktree": "qa_env",
            "tmux_window": "qa",
            "task_id": "qa-001"
        }

        token = jwt_manager.issue_token(
            agent_type=AgentType.QA,
            permissions=["test"],
            metadata=metadata
        )

        payload = jwt_manager.verify_token(token)

        assert payload["metadata"]["worktree"] == "qa_env"
        assert payload["metadata"]["tmux_window"] == "qa"
        assert payload["metadata"]["task_id"] == "qa-001"


class TestTokenStore:
    """Token Store テストケース"""

    @pytest.fixture
    def token_store(self, tmp_path):
        """Token Storeのフィクスチャ"""
        store_path = tmp_path / "token_store.json"
        return TokenStore(str(store_path))

    def test_add_token(self, token_store):
        """トークン追加テスト"""
        jti = "test-jti-12345"
        agent_type = AgentType.BUILDER
        expiry = datetime.now() + timedelta(hours=1)

        token_store.add_token(jti, agent_type, expiry)

        assert token_store.exists(jti) is True

    def test_revoke_token(self, token_store):
        """トークン失効テスト"""
        jti = "test-jti-67890"
        agent_type = AgentType.QA
        expiry = datetime.now() + timedelta(hours=1)

        token_store.add_token(jti, agent_type, expiry)
        token_store.revoke(jti)

        assert token_store.is_revoked(jti) is True

    def test_cleanup_expired_tokens(self, token_store):
        """期限切れトークンのクリーンアップテスト"""
        # 期限切れトークン
        jti_expired = "expired-token"
        token_store.add_token(
            jti_expired,
            AgentType.DEPLOYER,
            datetime.now() - timedelta(hours=1)
        )

        # 有効なトークン
        jti_valid = "valid-token"
        token_store.add_token(
            jti_valid,
            AgentType.SECURITY,
            datetime.now() + timedelta(hours=1)
        )

        # クリーンアップ実行
        cleaned_count = token_store.cleanup_expired()

        assert cleaned_count >= 1
        assert token_store.exists(jti_expired) is False
        assert token_store.exists(jti_valid) is True

    def test_persistence(self, tmp_path):
        """永続化テスト"""
        store_path = tmp_path / "persist_test.json"

        # 最初のインスタンス
        store1 = TokenStore(str(store_path))
        jti = "persist-test-token"
        store1.add_token(
            jti,
            AgentType.PERFORMANCE,
            datetime.now() + timedelta(hours=1)
        )

        # 新しいインスタンス（永続化されたデータをロード）
        store2 = TokenStore(str(store_path))

        assert store2.exists(jti) is True


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
