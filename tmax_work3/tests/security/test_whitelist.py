"""
Test cases for Whitelist Manager
エージェントホワイトリスト管理システムのテスト
"""
import pytest
from pathlib import Path
import sys

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from tmax_work3.security.whitelist import WhitelistManager
from tmax_work3.blackboard.state_manager import AgentType


class TestWhitelistManager:
    """Whitelist Manager テストケース"""

    @pytest.fixture
    def whitelist_manager(self, tmp_path):
        """Whitelist Managerのフィクスチャ"""
        whitelist_path = tmp_path / "whitelist.json"
        return WhitelistManager(str(whitelist_path))

    def test_add_agent_to_whitelist(self, whitelist_manager):
        """エージェントをホワイトリストに追加"""
        result = whitelist_manager.add_agent(
            agent_type=AgentType.BUILDER,
            permissions=["read", "write", "execute"],
            max_tokens=10,
            rate_limit_per_minute=60
        )

        assert result is True
        assert whitelist_manager.is_whitelisted(AgentType.BUILDER) is True

    def test_remove_agent_from_whitelist(self, whitelist_manager):
        """エージェントをホワイトリストから削除"""
        whitelist_manager.add_agent(
            agent_type=AgentType.QA,
            permissions=["read", "execute"]
        )

        assert whitelist_manager.is_whitelisted(AgentType.QA) is True

        result = whitelist_manager.remove_agent(AgentType.QA)
        assert result is True
        assert whitelist_manager.is_whitelisted(AgentType.QA) is False

    def test_check_permission(self, whitelist_manager):
        """権限チェックテスト"""
        whitelist_manager.add_agent(
            agent_type=AgentType.SECURITY,
            permissions=["read", "scan", "audit"]
        )

        # 許可された権限
        assert whitelist_manager.has_permission(AgentType.SECURITY, "read") is True
        assert whitelist_manager.has_permission(AgentType.SECURITY, "scan") is True

        # 許可されていない権限
        assert whitelist_manager.has_permission(AgentType.SECURITY, "write") is False
        assert whitelist_manager.has_permission(AgentType.SECURITY, "deploy") is False

    def test_check_permission_non_whitelisted_agent(self, whitelist_manager):
        """ホワイトリストに登録されていないエージェントの権限チェック"""
        # ホワイトリストに登録されていないエージェント
        result = whitelist_manager.has_permission(
            AgentType.DEPLOYER,
            "deploy"
        )

        assert result is False

    def test_get_agent_permissions(self, whitelist_manager):
        """エージェントの権限リスト取得"""
        permissions = ["build", "test", "deploy"]
        whitelist_manager.add_agent(
            agent_type=AgentType.BUILDER,
            permissions=permissions
        )

        retrieved_permissions = whitelist_manager.get_permissions(AgentType.BUILDER)

        assert set(retrieved_permissions) == set(permissions)

    def test_get_permissions_non_whitelisted_agent(self, whitelist_manager):
        """ホワイトリストに登録されていないエージェントの権限リスト取得"""
        permissions = whitelist_manager.get_permissions(AgentType.AUDIT)

        assert permissions == []

    def test_update_agent_permissions(self, whitelist_manager):
        """エージェント権限の更新"""
        whitelist_manager.add_agent(
            agent_type=AgentType.PERFORMANCE,
            permissions=["read"]
        )

        # 権限を更新
        result = whitelist_manager.update_permissions(
            agent_type=AgentType.PERFORMANCE,
            permissions=["read", "write", "monitor"]
        )

        assert result is True
        assert whitelist_manager.has_permission(AgentType.PERFORMANCE, "monitor") is True
        assert whitelist_manager.has_permission(AgentType.PERFORMANCE, "write") is True

    def test_token_limit(self, whitelist_manager):
        """トークン発行上限チェック"""
        max_tokens = 5
        whitelist_manager.add_agent(
            agent_type=AgentType.QA,
            permissions=["test"],
            max_tokens=max_tokens
        )

        # トークン使用を記録
        for i in range(max_tokens):
            can_issue = whitelist_manager.can_issue_token(AgentType.QA)
            assert can_issue is True
            whitelist_manager.record_token_issued(AgentType.QA)

        # 上限に達した後
        can_issue = whitelist_manager.can_issue_token(AgentType.QA)
        assert can_issue is False

    def test_rate_limit(self, whitelist_manager):
        """レート制限チェック"""
        rate_limit = 3
        whitelist_manager.add_agent(
            agent_type=AgentType.DEPLOYER,
            permissions=["deploy"],
            rate_limit_per_minute=rate_limit
        )

        # レート制限内
        for i in range(rate_limit):
            can_proceed = whitelist_manager.check_rate_limit(AgentType.DEPLOYER)
            assert can_proceed is True

        # レート制限超過
        can_proceed = whitelist_manager.check_rate_limit(AgentType.DEPLOYER)
        assert can_proceed is False

    def test_get_all_whitelisted_agents(self, whitelist_manager):
        """全ホワイトリストエージェント取得"""
        whitelist_manager.add_agent(AgentType.BUILDER, ["build"])
        whitelist_manager.add_agent(AgentType.QA, ["test"])
        whitelist_manager.add_agent(AgentType.SECURITY, ["scan"])

        agents = whitelist_manager.get_all_agents()

        assert len(agents) >= 3
        assert AgentType.BUILDER in agents
        assert AgentType.QA in agents
        assert AgentType.SECURITY in agents

    def test_persistence(self, tmp_path):
        """永続化テスト"""
        whitelist_path = tmp_path / "persist_whitelist.json"

        # 最初のインスタンス
        wl1 = WhitelistManager(str(whitelist_path))
        wl1.add_agent(
            agent_type=AgentType.COORDINATOR,
            permissions=["admin", "coordinate"]
        )

        # 新しいインスタンス（永続化されたデータをロード）
        wl2 = WhitelistManager(str(whitelist_path))

        assert wl2.is_whitelisted(AgentType.COORDINATOR) is True
        assert wl2.has_permission(AgentType.COORDINATOR, "admin") is True

    def test_default_permissions(self, whitelist_manager):
        """デフォルト権限テスト"""
        # デフォルト権限でエージェント追加
        whitelist_manager.add_agent(
            agent_type=AgentType.BUILDER,
            permissions=None  # デフォルト権限を使用
        )

        permissions = whitelist_manager.get_permissions(AgentType.BUILDER)

        # デフォルト権限が設定されていることを確認
        assert len(permissions) > 0
        assert "read" in permissions

    def test_reset_token_count(self, whitelist_manager):
        """トークンカウントリセットテスト"""
        whitelist_manager.add_agent(
            agent_type=AgentType.AUDIT,
            permissions=["audit"],
            max_tokens=5
        )

        # トークンを発行
        for i in range(3):
            whitelist_manager.record_token_issued(AgentType.AUDIT)

        # リセット
        whitelist_manager.reset_token_count(AgentType.AUDIT)

        # リセット後は再度発行可能
        can_issue = whitelist_manager.can_issue_token(AgentType.AUDIT)
        assert can_issue is True


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
