"""
Whitelist Manager - エージェントホワイトリスト管理
RBAC（Role-Based Access Control）とレート制限
"""
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Any
from threading import RLock
from collections import defaultdict

from tmax_work3.blackboard.state_manager import AgentType


class WhitelistManager:
    """
    ホワイトリストマネージャー - エージェント権限管理

    機能:
    - エージェントの登録/削除
    - 権限管理（RBAC）
    - トークン発行上限
    - レート制限
    """

    # デフォルト権限定義
    DEFAULT_PERMISSIONS = {
        AgentType.COORDINATOR: ["admin", "coordinate", "assign", "monitor"],
        AgentType.BUILDER: ["read", "write", "build", "test"],
        AgentType.QA: ["read", "test", "report"],
        AgentType.SECURITY: ["read", "scan", "audit", "report"],
        AgentType.DEPLOYER: ["read", "deploy", "rollback"],
        AgentType.PERFORMANCE: ["read", "monitor", "analyze"],
        AgentType.AUDIT: ["read", "audit", "report"],
    }

    def __init__(self, storage_path: str):
        """
        初期化

        Args:
            storage_path: ホワイトリストのファイルパス
        """
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

        self.lock = RLock()

        # ホワイトリストデータ
        # {agent_type: {permissions, max_tokens, rate_limit, token_count, rate_count, last_reset}}
        self.whitelist: Dict[str, Dict[str, Any]] = {}

        # レート制限カウンター
        # {agent_type: [(timestamp, count)]}
        self.rate_counters: Dict[str, List[float]] = defaultdict(list)

        # ロード
        self._load()

    def add_agent(
        self,
        agent_type: AgentType,
        permissions: Optional[List[str]] = None,
        max_tokens: int = 100,
        rate_limit_per_minute: int = 60
    ) -> bool:
        """
        エージェントをホワイトリストに追加

        Args:
            agent_type: エージェントタイプ
            permissions: 権限リスト（Noneの場合はデフォルト権限）
            max_tokens: 最大トークン発行数
            rate_limit_per_minute: 1分あたりのレート制限

        Returns:
            追加成功: True
        """
        with self.lock:
            # デフォルト権限を使用
            if permissions is None:
                permissions = self.DEFAULT_PERMISSIONS.get(
                    agent_type,
                    ["read"]
                )

            self.whitelist[agent_type.value] = {
                "permissions": permissions,
                "max_tokens": max_tokens,
                "rate_limit_per_minute": rate_limit_per_minute,
                "token_count": 0,
                "added_at": datetime.now().isoformat()
            }

            self._save()
            return True

    def remove_agent(self, agent_type: AgentType) -> bool:
        """
        エージェントをホワイトリストから削除

        Args:
            agent_type: エージェントタイプ

        Returns:
            削除成功: True, 存在しない: False
        """
        with self.lock:
            if agent_type.value in self.whitelist:
                del self.whitelist[agent_type.value]
                self._save()
                return True
            return False

    def is_whitelisted(self, agent_type: AgentType) -> bool:
        """
        エージェントがホワイトリストに登録されているか確認

        Args:
            agent_type: エージェントタイプ

        Returns:
            登録済み: True, 未登録: False
        """
        with self.lock:
            return agent_type.value in self.whitelist

    def has_permission(self, agent_type: AgentType, permission: str) -> bool:
        """
        エージェントが指定された権限を持っているか確認

        Args:
            agent_type: エージェントタイプ
            permission: 確認する権限

        Returns:
            権限あり: True, 権限なし: False
        """
        with self.lock:
            if not self.is_whitelisted(agent_type):
                return False

            permissions = self.whitelist[agent_type.value]["permissions"]
            return permission in permissions

    def get_permissions(self, agent_type: AgentType) -> List[str]:
        """
        エージェントの権限リストを取得

        Args:
            agent_type: エージェントタイプ

        Returns:
            権限リスト（未登録の場合は空リスト）
        """
        with self.lock:
            if not self.is_whitelisted(agent_type):
                return []

            return self.whitelist[agent_type.value]["permissions"].copy()

    def update_permissions(
        self,
        agent_type: AgentType,
        permissions: List[str]
    ) -> bool:
        """
        エージェントの権限を更新

        Args:
            agent_type: エージェントタイプ
            permissions: 新しい権限リスト

        Returns:
            更新成功: True, 失敗: False
        """
        with self.lock:
            if not self.is_whitelisted(agent_type):
                return False

            self.whitelist[agent_type.value]["permissions"] = permissions
            self._save()
            return True

    def can_issue_token(self, agent_type: AgentType) -> bool:
        """
        トークンを発行できるか確認（上限チェック）

        Args:
            agent_type: エージェントタイプ

        Returns:
            発行可能: True, 不可: False
        """
        with self.lock:
            if not self.is_whitelisted(agent_type):
                return False

            agent_data = self.whitelist[agent_type.value]
            token_count = agent_data.get("token_count", 0)
            max_tokens = agent_data.get("max_tokens", 100)

            return token_count < max_tokens

    def record_token_issued(self, agent_type: AgentType):
        """
        トークン発行を記録

        Args:
            agent_type: エージェントタイプ
        """
        with self.lock:
            if self.is_whitelisted(agent_type):
                self.whitelist[agent_type.value]["token_count"] += 1
                self._save()

    def reset_token_count(self, agent_type: AgentType):
        """
        トークンカウントをリセット

        Args:
            agent_type: エージェントタイプ
        """
        with self.lock:
            if self.is_whitelisted(agent_type):
                self.whitelist[agent_type.value]["token_count"] = 0
                self._save()

    def check_rate_limit(self, agent_type: AgentType) -> bool:
        """
        レート制限をチェック

        Args:
            agent_type: エージェントタイプ

        Returns:
            制限内: True, 制限超過: False
        """
        with self.lock:
            if not self.is_whitelisted(agent_type):
                return False

            agent_data = self.whitelist[agent_type.value]
            rate_limit = agent_data.get("rate_limit_per_minute", 60)

            # 1分前のタイムスタンプ
            one_minute_ago = datetime.now() - timedelta(minutes=1)
            one_minute_ago_ts = one_minute_ago.timestamp()

            # 古いカウンターを削除
            agent_key = agent_type.value
            self.rate_counters[agent_key] = [
                ts for ts in self.rate_counters[agent_key]
                if ts > one_minute_ago_ts
            ]

            # レート制限チェック
            current_count = len(self.rate_counters[agent_key])

            if current_count >= rate_limit:
                return False

            # カウンター追加
            self.rate_counters[agent_key].append(datetime.now().timestamp())
            return True

    def get_all_agents(self) -> List[AgentType]:
        """
        全ホワイトリストエージェントを取得

        Returns:
            エージェントタイプのリスト
        """
        with self.lock:
            return [
                AgentType(agent_str)
                for agent_str in self.whitelist.keys()
            ]

    def get_agent_info(self, agent_type: AgentType) -> Optional[Dict[str, Any]]:
        """
        エージェント情報を取得

        Args:
            agent_type: エージェントタイプ

        Returns:
            エージェント情報、存在しない場合はNone
        """
        with self.lock:
            if not self.is_whitelisted(agent_type):
                return None

            return self.whitelist[agent_type.value].copy()

    def _save(self):
        """状態を保存"""
        with open(self.storage_path, 'w', encoding='utf-8') as f:
            json.dump(self.whitelist, f, indent=2, ensure_ascii=False)

    def _load(self):
        """状態をロード"""
        if not self.storage_path.exists():
            return

        try:
            with open(self.storage_path, 'r', encoding='utf-8') as f:
                self.whitelist = json.load(f)
        except Exception as e:
            print(f"Warning: Failed to load whitelist: {e}")
            self.whitelist = {}


if __name__ == "__main__":
    # テスト実行
    wl = WhitelistManager("tmax_work3/security/test_whitelist.json")

    # エージェント追加
    wl.add_agent(
        agent_type=AgentType.BUILDER,
        permissions=["read", "write", "build"]
    )

    wl.add_agent(
        agent_type=AgentType.QA,
        permissions=["read", "test"]
    )

    # 権限チェック
    print(f"BUILDER has 'build' permission: {wl.has_permission(AgentType.BUILDER, 'build')}")
    print(f"BUILDER has 'deploy' permission: {wl.has_permission(AgentType.BUILDER, 'deploy')}")

    # トークン発行チェック
    for i in range(3):
        can_issue = wl.can_issue_token(AgentType.BUILDER)
        print(f"Can issue token ({i+1}): {can_issue}")
        if can_issue:
            wl.record_token_issued(AgentType.BUILDER)

    # 全エージェント取得
    agents = wl.get_all_agents()
    print(f"Whitelisted agents: {[a.value for a in agents]}")
