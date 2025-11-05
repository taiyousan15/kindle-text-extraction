"""
JWT Manager - A-JWT (Agent JWT) 管理システム
Zero-Trust認証のためのJWT発行・検証・失効
"""
import json
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List
from threading import RLock

from jose import jwt, JWTError

from tmax_work3.blackboard.state_manager import AgentType


class TokenStore:
    """
    トークンストア - 発行済みトークンの管理と失効リスト
    ファイルベースの永続化ストレージ
    """

    def __init__(self, storage_path: str):
        """
        初期化

        Args:
            storage_path: トークンストアのファイルパス
        """
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

        self.lock = RLock()

        # トークンデータ
        # {jti: {agent_type, issued_at, expires_at, revoked, metadata}}
        self.tokens: Dict[str, Dict[str, Any]] = {}

        # ロード
        self._load()

    def add_token(
        self,
        jti: str,
        agent_type: AgentType,
        expiry: datetime,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        トークンを追加

        Args:
            jti: JWT ID (nonce)
            agent_type: エージェントタイプ
            expiry: 有効期限
            metadata: 追加メタデータ
        """
        with self.lock:
            self.tokens[jti] = {
                "agent_type": agent_type.value,
                "issued_at": datetime.now().isoformat(),
                "expires_at": expiry.isoformat(),
                "revoked": False,
                "metadata": metadata or {}
            }
            self._save()

    def revoke(self, jti: str) -> bool:
        """
        トークンを失効

        Args:
            jti: JWT ID

        Returns:
            失効成功: True, 失敗: False
        """
        with self.lock:
            if jti in self.tokens:
                self.tokens[jti]["revoked"] = True
                self.tokens[jti]["revoked_at"] = datetime.now().isoformat()
                self._save()
                return True
            return False

    def is_revoked(self, jti: str) -> bool:
        """
        トークンが失効しているか確認

        Args:
            jti: JWT ID

        Returns:
            失効済み: True, 有効: False
        """
        with self.lock:
            if jti in self.tokens:
                return self.tokens[jti].get("revoked", False)
            return False

    def exists(self, jti: str) -> bool:
        """
        トークンが存在するか確認

        Args:
            jti: JWT ID

        Returns:
            存在: True, 存在しない: False
        """
        with self.lock:
            return jti in self.tokens

    def get_token_info(self, jti: str) -> Optional[Dict[str, Any]]:
        """
        トークン情報を取得

        Args:
            jti: JWT ID

        Returns:
            トークン情報、存在しない場合はNone
        """
        with self.lock:
            return self.tokens.get(jti)

    def get_active_tokens(self, agent_type: Optional[AgentType] = None) -> List[str]:
        """
        アクティブなトークンのリストを取得

        Args:
            agent_type: エージェントタイプでフィルタ（Noneの場合は全て）

        Returns:
            アクティブなトークンのJTIリスト
        """
        with self.lock:
            active = []
            now = datetime.now()

            for jti, info in self.tokens.items():
                # 失効していない
                if info.get("revoked", False):
                    continue

                # 有効期限内
                expires_at = datetime.fromisoformat(info["expires_at"])
                if expires_at < now:
                    continue

                # エージェントタイプでフィルタ
                if agent_type is not None:
                    if info["agent_type"] != agent_type.value:
                        continue

                active.append(jti)

            return active

    def cleanup_expired(self) -> int:
        """
        期限切れトークンをクリーンアップ

        Returns:
            削除されたトークン数
        """
        with self.lock:
            now = datetime.now()
            to_delete = []

            for jti, info in self.tokens.items():
                expires_at = datetime.fromisoformat(info["expires_at"])
                if expires_at < now:
                    to_delete.append(jti)

            for jti in to_delete:
                del self.tokens[jti]

            if to_delete:
                self._save()

            return len(to_delete)

    def _save(self):
        """状態を保存"""
        with open(self.storage_path, 'w', encoding='utf-8') as f:
            json.dump(self.tokens, f, indent=2, ensure_ascii=False)

    def _load(self):
        """状態をロード"""
        if not self.storage_path.exists():
            return

        try:
            with open(self.storage_path, 'r', encoding='utf-8') as f:
                self.tokens = json.load(f)
        except Exception as e:
            print(f"Warning: Failed to load token store: {e}")
            self.tokens = {}


class JWTManager:
    """
    JWT Manager - A-JWT発行・検証・失効システム
    HS256アルゴリズムを使用したJWT管理
    """

    def __init__(
        self,
        secret_key: str,
        algorithm: str = "HS256",
        token_expiry_hours: int = 1,
        token_store_path: Optional[str] = None
    ):
        """
        初期化

        Args:
            secret_key: JWT署名用の秘密鍵
            algorithm: JWTアルゴリズム（デフォルト: HS256）
            token_expiry_hours: トークン有効期限（時間）
            token_store_path: トークンストアのパス
        """
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.token_expiry_hours = token_expiry_hours

        # トークンストア
        if token_store_path is None:
            token_store_path = "tmax_work3/security/token_store.json"

        self.token_store = TokenStore(token_store_path)

        print(f"JWT Manager initialized (expiry: {token_expiry_hours}h)")

    def issue_token(
        self,
        agent_type: AgentType,
        permissions: List[str],
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        トークンを発行

        Args:
            agent_type: エージェントタイプ
            permissions: 権限リスト
            metadata: 追加メタデータ

        Returns:
            JWT文字列
        """
        # JWT ID (nonce) - リプレイ攻撃防止
        jti = str(uuid.uuid4())

        # タイムスタンプ
        now = datetime.now()
        expiry = now + timedelta(hours=self.token_expiry_hours)

        # ペイロード
        payload = {
            "jti": jti,
            "agent_type": agent_type.value,
            "permissions": permissions,
            "iat": int(now.timestamp()),
            "exp": int(expiry.timestamp()),
            "metadata": metadata or {}
        }

        # JWT生成
        token = jwt.encode(
            payload,
            self.secret_key,
            algorithm=self.algorithm
        )

        # トークンストアに追加
        self.token_store.add_token(jti, agent_type, expiry, metadata)

        return token

    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        トークンを検証

        Args:
            token: JWT文字列

        Returns:
            ペイロード（検証成功）、None（検証失敗）
        """
        try:
            # JWT検証
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm]
            )

            # JTI取得
            jti = payload.get("jti")
            if not jti:
                return None

            # 失効チェック
            if self.token_store.is_revoked(jti):
                return None

            return payload

        except JWTError as e:
            print(f"JWT verification failed: {e}")
            return None

    def revoke_token(self, jti: str) -> bool:
        """
        トークンを失効

        Args:
            jti: JWT ID

        Returns:
            失効成功: True, 失敗: False
        """
        return self.token_store.revoke(jti)

    def is_token_revoked(self, jti: str) -> bool:
        """
        トークンが失効しているか確認

        Args:
            jti: JWT ID

        Returns:
            失効済み: True, 有効: False
        """
        return self.token_store.is_revoked(jti)

    def get_active_tokens(self, agent_type: Optional[AgentType] = None) -> List[str]:
        """
        アクティブなトークンを取得

        Args:
            agent_type: エージェントタイプでフィルタ

        Returns:
            アクティブなJTIリスト
        """
        return self.token_store.get_active_tokens(agent_type)

    def cleanup_expired_tokens(self) -> int:
        """
        期限切れトークンをクリーンアップ

        Returns:
            削除されたトークン数
        """
        return self.token_store.cleanup_expired()


if __name__ == "__main__":
    # テスト実行
    jwt_manager = JWTManager(
        secret_key="test-secret-key",
        token_expiry_hours=1
    )

    # トークン発行
    token = jwt_manager.issue_token(
        agent_type=AgentType.BUILDER,
        permissions=["read", "write", "build"],
        metadata={"worktree": "build_env"}
    )

    print(f"Token issued: {token[:50]}...")

    # トークン検証
    payload = jwt_manager.verify_token(token)
    if payload:
        print(f"Token verified: {payload}")
    else:
        print("Token verification failed")

    # トークン失効
    jti = payload["jti"]
    jwt_manager.revoke_token(jti)
    print(f"Token revoked: {jti}")

    # 失効後の検証
    payload_after = jwt_manager.verify_token(token)
    print(f"Token after revocation: {payload_after}")
