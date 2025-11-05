"""
Auth Agent - Zero-Trust A-JWT認証エージェント

役割:
- エージェント認証（A-JWT発行）
- トークン検証・失効
- 権限管理（RBAC）
- ホワイトリスト管理
- 監査ログ記録
- リプレイ攻撃防止
"""
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
import sys

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from tmax_work3.security.jwt_manager import JWTManager
from tmax_work3.security.whitelist import WhitelistManager
from tmax_work3.blackboard.state_manager import (
    AgentType,
    get_blackboard
)


class AuthAgent:
    """
    Auth Agent - Zero-Trust認証システム

    特徴:
    - A-JWT（Agent JWT）による認証
    - RBAC（Role-Based Access Control）
    - ホワイトリストベースのアクセス制御
    - 監査ログの完全記録
    - リプレイ攻撃防止（nonce使用）
    - トークン失効リスト
    """

    def __init__(
        self,
        secret_key: str,
        storage_dir: Optional[str] = None,
        token_expiry_hours: int = 1
    ):
        """
        初期化

        Args:
            secret_key: JWT署名用の秘密鍵
            storage_dir: ストレージディレクトリ
            token_expiry_hours: トークン有効期限（時間）
        """
        if storage_dir is None:
            storage_dir = "tmax_work3/security"

        storage_path = Path(storage_dir)
        storage_path.mkdir(parents=True, exist_ok=True)

        # JWT Manager
        self.jwt_manager = JWTManager(
            secret_key=secret_key,
            algorithm="HS256",
            token_expiry_hours=token_expiry_hours,
            token_store_path=str(storage_path / "token_store.json")
        )

        # Whitelist Manager
        self.whitelist_manager = WhitelistManager(
            storage_path=str(storage_path / "whitelist.json")
        )

        # 監査ログ
        self.audit_log_path = storage_path / "audit_log.json"
        self.audit_logs: List[Dict[str, Any]] = []
        self._load_audit_logs()

        # Blackboard連携
        self.blackboard = get_blackboard()
        self.blackboard.register_agent(AgentType.SECURITY)

        self._log_info("Auth Agent initialized")

    def register_agent(
        self,
        agent_type: AgentType,
        permissions: Optional[List[str]] = None,
        max_tokens: int = 100,
        rate_limit_per_minute: int = 60
    ) -> bool:
        """
        エージェントを登録（ホワイトリストに追加）

        Args:
            agent_type: エージェントタイプ
            permissions: 権限リスト（Noneの場合はデフォルト）
            max_tokens: 最大トークン発行数
            rate_limit_per_minute: 1分あたりのレート制限

        Returns:
            登録成功: True, 失敗: False
        """
        result = self.whitelist_manager.add_agent(
            agent_type=agent_type,
            permissions=permissions,
            max_tokens=max_tokens,
            rate_limit_per_minute=rate_limit_per_minute
        )

        if result:
            self._log_audit(
                action="register_agent",
                agent_type=agent_type,
                details={
                    "permissions": permissions or "default",
                    "max_tokens": max_tokens,
                    "rate_limit": rate_limit_per_minute
                },
                status="success"
            )
            self._log_info(f"Agent registered: {agent_type.value}")
        else:
            self._log_audit(
                action="register_agent",
                agent_type=agent_type,
                status="failed",
                message="Registration failed"
            )

        return result

    def unregister_agent(self, agent_type: AgentType) -> bool:
        """
        エージェントの登録を解除

        Args:
            agent_type: エージェントタイプ

        Returns:
            解除成功: True, 失敗: False
        """
        result = self.whitelist_manager.remove_agent(agent_type)

        if result:
            self._log_audit(
                action="unregister_agent",
                agent_type=agent_type,
                status="success"
            )
            self._log_info(f"Agent unregistered: {agent_type.value}")

        return result

    def authenticate(
        self,
        agent_type: AgentType,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        エージェントを認証してトークンを発行

        Args:
            agent_type: エージェントタイプ
            metadata: 追加メタデータ

        Returns:
            JWT文字列（成功）、None（失敗）
        """
        # ホワイトリストチェック
        if not self.whitelist_manager.is_whitelisted(agent_type):
            self._log_audit(
                action="authenticate",
                agent_type=agent_type,
                status="failed",
                message="Agent not whitelisted"
            )
            return None

        # レート制限チェック
        if not self.whitelist_manager.check_rate_limit(agent_type):
            self._log_audit(
                action="authenticate",
                agent_type=agent_type,
                status="failed",
                message="Rate limit exceeded"
            )
            return None

        # トークン発行上限チェック
        if not self.whitelist_manager.can_issue_token(agent_type):
            self._log_audit(
                action="authenticate",
                agent_type=agent_type,
                status="failed",
                message="Token limit exceeded"
            )
            return None

        # 権限取得
        permissions = self.whitelist_manager.get_permissions(agent_type)

        # トークン発行
        token = self.jwt_manager.issue_token(
            agent_type=agent_type,
            permissions=permissions,
            metadata=metadata
        )

        # トークン発行を記録
        self.whitelist_manager.record_token_issued(agent_type)

        # 監査ログ
        self._log_audit(
            action="authenticate",
            agent_type=agent_type,
            status="success",
            details={
                "permissions": permissions,
                "metadata": metadata
            }
        )

        self._log_info(f"Token issued for {agent_type.value}")

        return token

    def verify(self, token: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        トークンを検証

        Args:
            token: JWT文字列

        Returns:
            (検証成功: True/False, ペイロード)
        """
        payload = self.jwt_manager.verify_token(token)

        if payload is None:
            self._log_audit(
                action="verify",
                status="failed",
                message="Token verification failed"
            )
            return False, None

        agent_type = AgentType(payload["agent_type"])

        self._log_audit(
            action="verify",
            agent_type=agent_type,
            status="success",
            details={"jti": payload["jti"]}
        )

        return True, payload

    def authorize(self, token: str, permission: str) -> bool:
        """
        トークンが指定された権限を持っているか確認

        Args:
            token: JWT文字列
            permission: 確認する権限

        Returns:
            権限あり: True, なし: False
        """
        # トークン検証
        is_valid, payload = self.verify(token)

        if not is_valid or payload is None:
            return False

        # 権限チェック
        permissions = payload.get("permissions", [])
        has_permission = permission in permissions

        agent_type = AgentType(payload["agent_type"])

        self._log_audit(
            action="authorize",
            agent_type=agent_type,
            status="success" if has_permission else "denied",
            details={
                "permission": permission,
                "has_permission": has_permission
            }
        )

        return has_permission

    def revoke(self, token: str) -> bool:
        """
        トークンを失効

        Args:
            token: JWT文字列

        Returns:
            失効成功: True, 失敗: False
        """
        # トークン検証（JTI取得）
        is_valid, payload = self.verify(token)

        if not is_valid or payload is None:
            return False

        jti = payload["jti"]
        agent_type = AgentType(payload["agent_type"])

        # 失効
        result = self.jwt_manager.revoke_token(jti)

        if result:
            self._log_audit(
                action="revoke",
                agent_type=agent_type,
                status="success",
                details={"jti": jti}
            )
            self._log_info(f"Token revoked: {jti}")

        return result

    def get_active_tokens(
        self,
        agent_type: Optional[AgentType] = None
    ) -> List[str]:
        """
        アクティブなトークンを取得

        Args:
            agent_type: エージェントタイプでフィルタ

        Returns:
            アクティブなJTIリスト
        """
        return self.jwt_manager.get_active_tokens(agent_type)

    def cleanup_expired_tokens(self) -> int:
        """
        期限切れトークンをクリーンアップ

        Returns:
            削除されたトークン数
        """
        count = self.jwt_manager.cleanup_expired_tokens()

        self._log_audit(
            action="cleanup",
            status="success",
            details={"cleaned_count": count}
        )

        return count

    def get_audit_logs(
        self,
        limit: int = 100,
        agent_type: Optional[AgentType] = None
    ) -> List[Dict[str, Any]]:
        """
        監査ログを取得

        Args:
            limit: 取得件数
            agent_type: エージェントタイプでフィルタ

        Returns:
            監査ログリスト
        """
        logs = self.audit_logs[-limit:]

        if agent_type is not None:
            logs = [
                log for log in logs
                if log.get("agent_type") == agent_type.value
            ]

        return logs

    def update_agent_permissions(
        self,
        agent_type: AgentType,
        permissions: List[str]
    ) -> bool:
        """
        エージェント権限を更新

        Args:
            agent_type: エージェントタイプ
            permissions: 新しい権限リスト

        Returns:
            更新成功: True, 失敗: False
        """
        result = self.whitelist_manager.update_permissions(
            agent_type=agent_type,
            permissions=permissions
        )

        if result:
            self._log_audit(
                action="update_permissions",
                agent_type=agent_type,
                status="success",
                details={"new_permissions": permissions}
            )

        return result

    def _log_audit(
        self,
        action: str,
        agent_type: Optional[AgentType] = None,
        status: str = "success",
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        監査ログを記録

        Args:
            action: アクション名
            agent_type: エージェントタイプ
            status: ステータス
            message: メッセージ
            details: 詳細情報
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "agent_type": agent_type.value if agent_type else None,
            "status": status,
            "message": message,
            "details": details or {}
        }

        self.audit_logs.append(log_entry)

        # ログが大きくなりすぎないよう制限
        if len(self.audit_logs) > 10000:
            self.audit_logs = self.audit_logs[-10000:]

        # 保存
        self._save_audit_logs()

    def _log_info(self, message: str):
        """Blackboardにログ記録"""
        self.blackboard.log(
            message,
            level="INFO",
            agent=AgentType.SECURITY
        )

    def _save_audit_logs(self):
        """監査ログを保存"""
        try:
            with open(self.audit_log_path, 'w', encoding='utf-8') as f:
                json.dump(self.audit_logs[-1000:], f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Warning: Failed to save audit logs: {e}")

    def _load_audit_logs(self):
        """監査ログをロード"""
        if not self.audit_log_path.exists():
            return

        try:
            with open(self.audit_log_path, 'r', encoding='utf-8') as f:
                self.audit_logs = json.load(f)
        except Exception as e:
            print(f"Warning: Failed to load audit logs: {e}")
            self.audit_logs = []


def main():
    """メイン実行例"""
    import os

    # 秘密鍵（実運用では環境変数から取得）
    secret_key = os.environ.get("AUTH_SECRET_KEY", "default-secret-key-change-me")

    # Auth Agent初期化
    auth_agent = AuthAgent(secret_key=secret_key)

    # エージェント登録
    print("\n=== Agent Registration ===")
    auth_agent.register_agent(
        agent_type=AgentType.BUILDER,
        permissions=["read", "write", "build"]
    )

    auth_agent.register_agent(
        agent_type=AgentType.QA,
        permissions=["read", "test", "report"]
    )

    # 認証（トークン発行）
    print("\n=== Authentication ===")
    builder_token = auth_agent.authenticate(
        agent_type=AgentType.BUILDER,
        metadata={"worktree": "build_env", "task_id": "build-001"}
    )

    print(f"Builder token: {builder_token[:50]}...")

    # トークン検証
    print("\n=== Token Verification ===")
    is_valid, payload = auth_agent.verify(builder_token)
    print(f"Token valid: {is_valid}")
    print(f"Payload: {json.dumps(payload, indent=2)}")

    # 権限チェック
    print("\n=== Authorization ===")
    can_build = auth_agent.authorize(builder_token, "build")
    print(f"Can build: {can_build}")

    can_deploy = auth_agent.authorize(builder_token, "deploy")
    print(f"Can deploy: {can_deploy}")

    # トークン失効
    print("\n=== Token Revocation ===")
    auth_agent.revoke(builder_token)

    is_valid_after, _ = auth_agent.verify(builder_token)
    print(f"Token valid after revocation: {is_valid_after}")

    # 監査ログ
    print("\n=== Audit Logs ===")
    logs = auth_agent.get_audit_logs(limit=10)
    for log in logs:
        print(f"{log['timestamp']}: {log['action']} - {log['status']}")


if __name__ == "__main__":
    main()
