# Miyabi Agent セットアップ完了

Kindle文字起こしツールプロジェクトに Miyabi Autonomous Agent システムが導入されました。

## 📁 導入された構成

```
.claude/
├── README.md                    # Miyabi システム説明
├── settings.local.json          # Claude Code 設定
├── mcp.json                     # MCP サーバー設定
│
├── agents/                      # Agent定義
│   ├── coordinator-agent.md     # CoordinatorAgent
│   ├── codegen-agent.md         # CodeGenAgent
│   ├── review-agent.md          # ReviewAgent
│   ├── issue-agent.md           # IssueAgent
│   ├── pr-agent.md              # PRAgent
│   ├── deployment-agent.md      # DeploymentAgent
│   └── error-hunter/            # エラー診断Agent群
│       ├── symptom-analyzer.md
│       ├── root-cause-detective.md
│       ├── safe-patcher.md
│       ├── test-guardian.md
│       ├── prevention-architect.md
│       └── coordinator.md
│
├── commands/                    # カスタムスラッシュコマンド
│   ├── miyabi-agent.md          # /miyabi-agent
│   ├── miyabi-status.md         # /miyabi-status
│   ├── miyabi-init.md           # /miyabi-init
│   ├── miyabi-auto.md           # /miyabi-auto
│   ├── miyabi-todos.md          # /miyabi-todos
│   ├── hunt-error.md            # /hunt-error
│   ├── test.md                  # /test
│   ├── deploy.md                # /deploy
│   ├── verify.md                # /verify
│   ├── security-scan.md         # /security-scan
│   ├── generate-docs.md         # /generate-docs
│   └── create-issue.md          # /create-issue
│
├── hooks/                       # Claude Hooks
│   └── log-commands.sh          # コマンドログ
│
└── mcp-servers/                 # MCPサーバー実装
    ├── github-enhanced.js       # GitHub統合
    ├── ide-integration.js       # IDE統合
    ├── miyabi-integration.js    # Miyabi CLI統合
    └── project-context.js       # プロジェクトコンテキスト
```

## 🚀 セットアップ手順

### 1. 環境変数の設定

`.env` ファイルを作成してください（`.env.example` を参考に）:

```bash
cp .env.example .env
```

必要な環境変数を設定:

```bash
# GitHub Configuration
GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
REPOSITORY=owner/repo

# Anthropic API (for CodeGenAgent)
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Device Identifier
DEVICE_IDENTIFIER=MacBook Pro 16-inch
```

### 2. GitHub トークンの取得

1. https://github.com/settings/tokens にアクセス
2. "Generate new token (classic)" をクリック
3. 以下の権限を選択:
   - `repo` (フルアクセス)
   - `workflow` (GitHub Actions)
4. トークンを生成して `.env` の `GITHUB_TOKEN` に設定

### 3. Anthropic API キーの取得

1. https://console.anthropic.com/ にログイン
2. "API Keys" セクションでキーを生成
3. `.env` の `ANTHROPIC_API_KEY` に設定

## 🤖 利用可能な MCP サーバー

### 1. **Miyabi Integration**
Miyabi CLI を Claude Code から直接操作

**提供ツール**:
- `miyabi__init` - 新規プロジェクト作成
- `miyabi__agent_run` - Autonomous Agent実行
- `miyabi__auto` - Water Spider全自動モード
- `miyabi__status` - プロジェクトステータス確認
- `miyabi__todos` - TODOコメント検出

### 2. **IDE Integration**
VS Code診断、Jupyter実行

**提供ツール**:
- `mcp__ide__getDiagnostics` - 診断情報取得
- `mcp__ide__executeCode` - Jupyter実行

### 3. **GitHub Enhanced**
Issue/PR管理の拡張機能

**提供ツール**:
- Issue操作（作成、更新、ラベル付け）
- PR作成・管理
- Projects V2 統合

### 4. **Project Context**
依存関係情報の提供

**提供ツール**:
- package.json 解析
- 依存グラフ生成

### 5. **Context Engineering** (オプション)
AI駆動のコンテキスト分析・最適化

**提供ツール**:
- セマンティック検索
- コンテキスト最適化
- 品質分析

**起動方法**:
```bash
cd external/context-engineering-mcp
uvicorn main:app --port 8888
```

### 6. **dev3000** (オプション)
UI/UX統合デバッグツール

**提供ツール**:
- サーバー・ブラウザ・ネットワーク統合ロギング
- 83%デバッグ時間削減

## 🎯 カスタムコマンド

Claude Code 内で以下のコマンドが使えます:

### Miyabi コマンド

- `/miyabi-init` - 新規プロジェクト作成
- `/miyabi-agent` - Issue自動処理
- `/miyabi-auto` - 全自動モード起動
- `/miyabi-status` - ステータス確認
- `/miyabi-todos` - TODO検出

### エラーハンティング

- `/hunt-error` - エラー診断・修正Agent起動

### 開発コマンド

- `/test` - テスト実行
- `/verify` - 動作確認
- `/deploy` - デプロイ実行
- `/security-scan` - セキュリティスキャン
- `/generate-docs` - ドキュメント生成
- `/create-issue` - Issue作成

## 📚 使い方

### 例1: プロジェクトステータス確認

```
あなた: "プロジェクトのステータスを確認して"
Claude: [miyabi__status を自動実行]
```

### 例2: Issue自動処理

```
あなた: "Issue #123を処理して"
Claude: [miyabi__agent_run({ issueNumber: 123 }) を自動実行]
```

### 例3: 全自動モード

```
あなた: "未処理のIssueを自動で処理して"
Claude: [miyabi__auto を自動実行]
```

### 例4: エラー診断

```
あなた: "/hunt-error"
Claude: [Error Hunter Agent群を起動して診断]
```

## 🏗️ Agent階層構造

```
Human Layer (戦略・承認)
    ├── TechLead
    ├── PO
    └── CISO
        ↓ Escalation
Coordinator Layer
    └── CoordinatorAgent (タスク分解・並行実行制御)
        ↓ Assignment
Specialist Layer
    ├── CodeGenAgent (AI駆動コード生成)
    ├── ReviewAgent (品質評価・80点基準)
    ├── IssueAgent (Issue分析・Label付与)
    ├── PRAgent (PR自動作成)
    └── DeploymentAgent (CI/CD・Firebase)
```

## ⚙️ 品質基準

### Review基準（80点以上合格）

```
品質スコア計算:
  基準点: 100点
  - ESLintエラー: -20点/件
  - TypeScriptエラー: -30点/件
  - Critical脆弱性: -40点/件
  合格ライン: 80点以上
```

## 🔒 セキュリティ

**重要**: 以下のファイルは `.gitignore` に追加してください:

- `.env` - 機密情報を含む
- `.claude/settings.local.json` - ローカル設定

## 📖 詳細ドキュメント

- `.claude/README.md` - Miyabiシステム完全ガイド
- `.claude/agents/` - 各Agent詳細仕様
- `.claude/commands/` - コマンド詳細説明

## 🌸 Miyabi とは

**Miyabi (雅)** = Beauty in Autonomous Development

日本の美意識「雅（みやび）」からインスピレーションを得た、
AI駆動の自律的開発システムです。

---

**セットアップ完了日**: 2025-10-27
**管理**: Miyabi Autonomous System

🤖 Generated with [Claude Code](https://claude.com/claude-code)
