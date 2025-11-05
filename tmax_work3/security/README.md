# Auth Agent - Zero-Trust A-JWT認証システム

## 概要

Auth Agent は、T-Max Work3 エージェントシステムのための Zero-Trust セキュリティ層です。A-JWT (Agent JWT) による認証、RBAC (Role-Based Access Control)、ホワイトリスト管理、監査ログ、リプレイ攻撃防止を提供します。

## 主な機能

### 1. A-JWT (Agent JWT) 認証
- **JWT発行**: HS256アルゴリズムによる署名付きトークン
- **トークン検証**: 署名検証、有効期限チェック、失効リスト確認
- **トークン失効**: 即座のトークン無効化
- **リプレイ攻撃防止**: ユニークなnonce (jti) による防御

### 2. RBAC (Role-Based Access Control)
- エージェントタイプごとの権限管理
- 細粒度の権限チェック
- 動的な権限更新

### 3. ホワイトリスト管理
- エージェント登録/削除
- トークン発行上限
- レート制限（1分あたりの要求数）

### 4. 監査ログ
- 全認証・認可操作の記録
- タイムスタンプ付きログ
- JSON形式で永続化

### 5. トークンストア
- ファイルベースの永続化
- 期限切れトークンの自動クリーンアップ
- アクティブトークンの追跡

## アーキテクチャ

```
┌─────────────────────────────────────────────────────┐
│                   Auth Agent                        │
│                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────┐ │
│  │ JWT Manager  │  │  Whitelist   │  │  Audit   │ │
│  │              │  │   Manager    │  │   Log    │ │
│  │ - Issue      │  │ - Register   │  │ - Record │ │
│  │ - Verify     │  │ - Permissions│  │ - Query  │ │
│  │ - Revoke     │  │ - Rate Limit │  │          │ │
│  └──────────────┘  └──────────────┘  └──────────┘ │
│         │                  │                 │     │
│         └──────────────────┴─────────────────┘     │
│                           │                        │
└───────────────────────────┼────────────────────────┘
                            │
                  ┌─────────┴─────────┐
                  │    Blackboard     │
                  │   (State Store)   │
                  └───────────────────┘
```

## ファイル構成

```
tmax_work3/
├── security/
│   ├── __init__.py              # モジュール初期化
│   ├── jwt_manager.py           # JWT発行・検証・失効
│   ├── whitelist.py             # ホワイトリスト管理
│   ├── token_store.json         # トークンストア（自動生成）
│   ├── whitelist.json           # ホワイトリスト（自動生成）
│   └── audit_log.json           # 監査ログ（自動生成）
├── agents/
│   └── auth.py                  # Auth Agentメインクラス
├── tests/
│   └── security/
│       ├── test_jwt_manager.py  # JWTテスト（12テスト）
│       ├── test_whitelist.py    # ホワイトリストテスト（13テスト）
│       └── test_auth_agent.py   # 統合テスト（15テスト）
└── examples/
    └── auth_integration_example.py  # 統合デモ
```

## 使用方法

### 1. Auth Agentの初期化

```python
from tmax_work3.agents.auth import AuthAgent

# Auth Agent初期化
auth_agent = AuthAgent(
    secret_key="your-secret-key-here",  # 本番環境では環境変数から取得
    storage_dir="tmax_work3/security",
    token_expiry_hours=1
)
```

### 2. エージェント登録

```python
from tmax_work3.blackboard.state_manager import AgentType

# エージェントをホワイトリストに登録
auth_agent.register_agent(
    agent_type=AgentType.BUILDER,
    permissions=["read", "write", "build"],
    max_tokens=100,
    rate_limit_per_minute=60
)
```

### 3. 認証（トークン発行）

```python
# トークン発行
token = auth_agent.authenticate(
    agent_type=AgentType.BUILDER,
    metadata={
        "worktree": "build_env",
        "task_id": "build-001"
    }
)

print(f"Token: {token}")
```

### 4. トークン検証

```python
# トークン検証
is_valid, payload = auth_agent.verify(token)

if is_valid:
    print(f"Agent: {payload['agent_type']}")
    print(f"Permissions: {payload['permissions']}")
    print(f"JTI: {payload['jti']}")
else:
    print("Invalid token")
```

### 5. 権限チェック

```python
# 特定の権限をチェック
can_build = auth_agent.authorize(token, "build")

if can_build:
    print("Agent is authorized to build")
else:
    print("Agent does not have build permission")
```

### 6. トークン失効

```python
# トークンを失効
result = auth_agent.revoke(token)

if result:
    print("Token revoked successfully")
```

### 7. 監査ログ取得

```python
# 監査ログを取得
logs = auth_agent.get_audit_logs(limit=10)

for log in logs:
    print(f"{log['timestamp']}: {log['action']} - {log['status']}")
```

## デフォルト権限

エージェントタイプごとのデフォルト権限:

| Agent Type | Default Permissions |
|-----------|---------------------|
| COORDINATOR | admin, coordinate, assign, monitor |
| BUILDER | read, write, build, test |
| QA | read, test, report |
| SECURITY | read, scan, audit, report |
| DEPLOYER | read, deploy, rollback |
| PERFORMANCE | read, monitor, analyze |
| AUDIT | read, audit, report |

## セキュリティ機能

### リプレイ攻撃防止

各トークンはユニークなJWT ID (jti) を持ち、同じトークンを複数回使用する攻撃を防ぎます。

```python
# 2つの異なるトークンは異なるjtiを持つ
token1 = auth_agent.authenticate(AgentType.BUILDER)
token2 = auth_agent.authenticate(AgentType.BUILDER)

_, payload1 = auth_agent.verify(token1)
_, payload2 = auth_agent.verify(token2)

assert payload1['jti'] != payload2['jti']  # 異なるnonce
```

### トークン発行上限

エージェントごとにトークン発行数を制限できます。

```python
# 最大5トークンまで
auth_agent.register_agent(
    agent_type=AgentType.QA,
    permissions=["test"],
    max_tokens=5
)
```

### レート制限

1分あたりの認証要求数を制限できます。

```python
# 1分あたり最大60回まで
auth_agent.register_agent(
    agent_type=AgentType.BUILDER,
    permissions=["build"],
    rate_limit_per_minute=60
)
```

## Coordinatorとの統合

Auth Agentは既存のCoordinatorとシームレスに統合できます:

```python
from tmax_work3.agents.coordinator import CoordinatorAgent
from tmax_work3.agents.auth import AuthAgent
from tmax_work3.blackboard.state_manager import AgentType

# Coordinator初期化
coordinator = CoordinatorAgent(
    repository_path=".",
    deploy_target="production"
)

# Auth Agent初期化
auth_agent = AuthAgent(secret_key="coordinator-secret")

# 全エージェントを登録
for agent_type in [AgentType.BUILDER, AgentType.QA, AgentType.DEPLOYER]:
    auth_agent.register_agent(agent_type)

# タスク実行前にトークン検証
def execute_task_with_auth(task, token):
    # トークン検証
    is_valid, payload = auth_agent.verify(token)

    if not is_valid:
        print("Authentication failed")
        return False

    # 権限チェック
    required_permission = task.get_required_permission()
    if not auth_agent.authorize(token, required_permission):
        print(f"Authorization failed: missing {required_permission} permission")
        return False

    # タスク実行
    coordinator.execute_task(task)
    return True
```

## テスト実行

```bash
# 全テストを実行
pytest tmax_work3/tests/security/ -v

# 特定のテストのみ実行
pytest tmax_work3/tests/security/test_jwt_manager.py -v
pytest tmax_work3/tests/security/test_whitelist.py -v
pytest tmax_work3/tests/security/test_auth_agent.py -v

# 統合デモを実行
python3 tmax_work3/examples/auth_integration_example.py
```

## テスト結果

```
========== 40 passed in 1.10s ==========

JWT Manager:      12 tests ✓
Whitelist:        13 tests ✓
Auth Agent:       15 tests ✓
```

## 環境変数

本番環境では以下の環境変数を設定してください:

```bash
# JWT秘密鍵（必須）
export AUTH_SECRET_KEY="your-production-secret-key-here"

# トークン有効期限（オプション、デフォルト: 1時間）
export AUTH_TOKEN_EXPIRY_HOURS=1

# ストレージディレクトリ（オプション）
export AUTH_STORAGE_DIR="tmax_work3/security"
```

## セキュリティベストプラクティス

1. **秘密鍵の管理**
   - 環境変数から秘密鍵を取得
   - 秘密鍵をコードにハードコードしない
   - 定期的に秘密鍵をローテーション

2. **トークン有効期限**
   - 短い有効期限を設定（1時間推奨）
   - 長期実行タスクには別の認証機構を検討

3. **監査ログ**
   - 定期的にログを確認
   - 異常なパターンを検出

4. **権限の最小化**
   - 必要最小限の権限のみ付与
   - 定期的に権限を見直し

5. **レート制限**
   - 適切なレート制限を設定
   - DoS攻撃を防止

## トラブルシューティング

### トークン検証失敗

```python
is_valid, payload = auth_agent.verify(token)
if not is_valid:
    # 原因をチェック
    # 1. トークンが失効している
    # 2. トークンが期限切れ
    # 3. 秘密鍵が一致しない
    # 4. トークンが改ざんされている
```

### 権限エラー

```python
can_proceed = auth_agent.authorize(token, "deploy")
if not can_proceed:
    # 権限を確認
    permissions = auth_agent.whitelist_manager.get_permissions(agent_type)
    print(f"Available permissions: {permissions}")
```

### レート制限超過

```python
token = auth_agent.authenticate(agent_type)
if token is None:
    # レート制限をチェック
    # しばらく待ってから再試行
    time.sleep(60)  # 1分待機
```

## ライセンス

このプロジェクトはT-Max Work3プロジェクトの一部です。

## 貢献

バグ報告や機能リクエストはIssueで受け付けています。

## 参考資料

- [JWT.io](https://jwt.io/) - JWT標準仕様
- [OWASP Top 10](https://owasp.org/www-project-top-ten/) - セキュリティベストプラクティス
- [Zero Trust Architecture](https://www.nist.gov/publications/zero-trust-architecture) - NIST Zero Trust ガイドライン
