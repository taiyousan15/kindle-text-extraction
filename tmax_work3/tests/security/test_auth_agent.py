"""
Test cases for Auth Agent
Zero-Trust A-JWT認証エージェントの統合テスト
"""
import pytest
from pathlib import Path
import sys
import time

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from tmax_work3.agents.auth import AuthAgent
from tmax_work3.blackboard.state_manager import AgentType, get_blackboard


class TestAuthAgent:
    """Auth Agent 統合テストケース"""

    @pytest.fixture
    def auth_agent(self, tmp_path):
        """Auth Agentのフィクスチャ"""
        return AuthAgent(
            secret_key="test-auth-secret-key",
            storage_dir=str(tmp_path)
        )

    @pytest.fixture
    def blackboard(self, tmp_path):
        """Blackboardのフィクスチャ"""
        from tmax_work3.blackboard.state_manager import Blackboard
        bb_path = tmp_path / "blackboard_state.json"
        return Blackboard(str(bb_path))

    def test_initialize_auth_agent(self, auth_agent):
        """Auth Agent初期化テスト"""
        assert auth_agent is not None
        assert auth_agent.jwt_manager is not None
        assert auth_agent.whitelist_manager is not None

    def test_register_agent_with_auth(self, auth_agent):
        """エージェント登録と認証テスト"""
        result = auth_agent.register_agent(
            agent_type=AgentType.BUILDER,
            permissions=["read", "write", "build"]
        )

        assert result is True

    def test_authenticate_agent(self, auth_agent):
        """エージェント認証テスト"""
        # エージェント登録
        auth_agent.register_agent(
            agent_type=AgentType.QA,
            permissions=["read", "test"]
        )

        # トークン発行
        token = auth_agent.authenticate(
            agent_type=AgentType.QA,
            metadata={"task_id": "qa-001"}
        )

        assert token is not None
        assert isinstance(token, str)

    def test_verify_agent_token(self, auth_agent):
        """トークン検証テスト"""
        auth_agent.register_agent(
            agent_type=AgentType.SECURITY,
            permissions=["scan", "audit"]
        )

        token = auth_agent.authenticate(AgentType.SECURITY)

        # トークン検証
        is_valid, payload = auth_agent.verify(token)

        assert is_valid is True
        assert payload is not None
        assert payload["agent_type"] == AgentType.SECURITY.value

    def test_authorize_permission(self, auth_agent):
        """権限チェックテスト"""
        auth_agent.register_agent(
            agent_type=AgentType.DEPLOYER,
            permissions=["deploy", "rollback"]
        )

        token = auth_agent.authenticate(AgentType.DEPLOYER)

        # 許可された権限
        is_authorized = auth_agent.authorize(token, "deploy")
        assert is_authorized is True

        # 許可されていない権限
        is_authorized = auth_agent.authorize(token, "admin")
        assert is_authorized is False

    def test_revoke_agent_token(self, auth_agent):
        """トークン失効テスト"""
        auth_agent.register_agent(
            agent_type=AgentType.PERFORMANCE,
            permissions=["monitor"]
        )

        token = auth_agent.authenticate(AgentType.PERFORMANCE)

        # トークン検証（有効）
        is_valid, _ = auth_agent.verify(token)
        assert is_valid is True

        # トークン失効
        result = auth_agent.revoke(token)
        assert result is True

        # 失効後の検証（無効）
        is_valid, _ = auth_agent.verify(token)
        assert is_valid is False

    def test_unregister_agent(self, auth_agent):
        """エージェント登録解除テスト"""
        auth_agent.register_agent(
            agent_type=AgentType.AUDIT,
            permissions=["audit"]
        )

        # 登録解除
        result = auth_agent.unregister_agent(AgentType.AUDIT)
        assert result is True

        # 登録解除後は認証できない
        token = auth_agent.authenticate(AgentType.AUDIT)
        assert token is None

    def test_audit_log_recording(self, auth_agent):
        """監査ログ記録テスト"""
        auth_agent.register_agent(
            agent_type=AgentType.BUILDER,
            permissions=["build"]
        )

        token = auth_agent.authenticate(AgentType.BUILDER)
        auth_agent.verify(token)
        auth_agent.authorize(token, "build")

        # 監査ログを取得
        logs = auth_agent.get_audit_logs(limit=10)

        assert len(logs) > 0
        # 認証ログが記録されているはず
        auth_logs = [log for log in logs if log["action"] == "authenticate"]
        assert len(auth_logs) > 0

    def test_failed_authentication_logging(self, auth_agent):
        """認証失敗時のログ記録テスト"""
        # ホワイトリストに登録されていないエージェント
        token = auth_agent.authenticate(AgentType.COORDINATOR)

        assert token is None

        # 失敗ログを確認
        logs = auth_agent.get_audit_logs(limit=10)
        failed_logs = [
            log for log in logs
            if log.get("status") == "failed" or
            (log.get("message") and "failed" in log.get("message", "").lower())
        ]

        assert len(failed_logs) > 0

    def test_rate_limiting(self, auth_agent):
        """レート制限テスト"""
        auth_agent.register_agent(
            agent_type=AgentType.QA,
            permissions=["test"],
            rate_limit_per_minute=3
        )

        # レート制限内
        for i in range(3):
            token = auth_agent.authenticate(AgentType.QA)
            assert token is not None

        # レート制限超過
        token = auth_agent.authenticate(AgentType.QA)
        assert token is None

    def test_token_limit(self, auth_agent):
        """トークン発行上限テスト"""
        max_tokens = 2
        auth_agent.register_agent(
            agent_type=AgentType.DEPLOYER,
            permissions=["deploy"],
            max_tokens=max_tokens
        )

        # 上限内
        tokens = []
        for i in range(max_tokens):
            token = auth_agent.authenticate(AgentType.DEPLOYER)
            assert token is not None
            tokens.append(token)

        # 上限超過
        token = auth_agent.authenticate(AgentType.DEPLOYER)
        assert token is None

        # トークンを失効すると再度発行可能
        auth_agent.revoke(tokens[0])
        token = auth_agent.authenticate(AgentType.DEPLOYER)
        # トークンカウントは失効してもリセットされない仕様の場合
        # assert token is None

    def test_get_active_tokens(self, auth_agent):
        """アクティブトークン取得テスト"""
        auth_agent.register_agent(
            agent_type=AgentType.SECURITY,
            permissions=["scan"]
        )

        # トークンを複数発行
        token1 = auth_agent.authenticate(AgentType.SECURITY)
        token2 = auth_agent.authenticate(AgentType.SECURITY)

        active_tokens = auth_agent.get_active_tokens(AgentType.SECURITY)

        assert len(active_tokens) >= 2

    def test_cleanup_expired_tokens(self, auth_agent):
        """期限切れトークンのクリーンアップテスト"""
        auth_agent.register_agent(
            agent_type=AgentType.PERFORMANCE,
            permissions=["monitor"]
        )

        # トークン発行
        token = auth_agent.authenticate(AgentType.PERFORMANCE)

        # クリーンアップ実行（期限切れトークンを削除）
        cleaned_count = auth_agent.cleanup_expired_tokens()

        # まだ有効なトークンは削除されない
        is_valid, _ = auth_agent.verify(token)
        assert is_valid is True

    def test_replay_attack_prevention(self, auth_agent):
        """リプレイ攻撃防止テスト"""
        auth_agent.register_agent(
            agent_type=AgentType.BUILDER,
            permissions=["build"]
        )

        # 2つのトークンを発行
        token1 = auth_agent.authenticate(AgentType.BUILDER)
        token2 = auth_agent.authenticate(AgentType.BUILDER)

        # トークンが異なることを確認
        assert token1 != token2

        # 両方とも有効
        is_valid1, payload1 = auth_agent.verify(token1)
        is_valid2, payload2 = auth_agent.verify(token2)

        assert is_valid1 is True
        assert is_valid2 is True

        # 異なるnonce（jti）を持つことを確認
        assert payload1["jti"] != payload2["jti"]

    def test_integration_with_blackboard(self, auth_agent, blackboard):
        """Blackboardとの統合テスト"""
        # エージェント登録（Blackboardにも登録）
        blackboard.register_agent(AgentType.BUILDER)

        # Auth Agentでも登録
        auth_agent.register_agent(
            agent_type=AgentType.BUILDER,
            permissions=["build"]
        )

        # トークン発行
        token = auth_agent.authenticate(AgentType.BUILDER)

        # Blackboardの状態を確認
        assert AgentType.BUILDER in blackboard.agents

        # トークン検証
        is_valid, payload = auth_agent.verify(token)
        assert is_valid is True


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
