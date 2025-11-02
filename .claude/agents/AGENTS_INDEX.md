# エージェント一覧 (Agent Index)

このディレクトリには、プロジェクト開発をサポートする21個の専門エージェントが格納されています。

## 📋 全エージェント一覧

### 🏗️ 開発・機能実装エージェント

1. **autonomous-feature-builder.md**
   - 完全な機能実装（要件から本番デプロイまで）
   - TDD（テスト駆動開発）アプローチ
   - 既存コードベースパターンの理解と統合

2. **codegen-agent.md**
   - AI駆動コード生成
   - Claude Sonnet 4による自動コード生成

### 🔍 デバッグ・エラー解決エージェント

3. **expert-debugger.md**
   - テスト失敗、エラーログ、例外スタックトレースの分析
   - ランタイムエラー、CI/CDパイプライン失敗の解決
   - 体系的なデバッグと根本原因分析

4. **error-resolver.md**
   - バグ、例外、ランタイムエラーの体系的な診断と修復
   - 失敗したテスト、壊れたコードの修正

5. **systematic-debugger.md**
   - 英語・日本語のエラーメッセージ対応
   - スタックトレース分析、テスト失敗のデバッグ
   - CI/CDパイプライン失敗調査

### 🛡️ Error Hunter チーム（エラー予防・解決専門）

6. **error-hunter-coordinator.md**
   - Error Hunterチーム全体の統括
   - タスクの優先順位付けと専門エージェントへの割り当て

7. **error-hunter-symptom-analyzer.md**
   - エラー症状の初期分析
   - エラーの分類とトリアージ

8. **error-hunter-root-cause-detective.md**
   - 根本原因の徹底調査
   - ディープダイブ分析

9. **error-hunter-safe-patcher.md**
   - 安全な修正パッチの適用
   - リスク最小化のコード修正

10. **error-hunter-test-guardian.md**
    - テスト戦略の設計と実装
    - テストカバレッジの向上

11. **error-hunter-prevention-architect.md**
    - 再発防止策の設計
    - システム全体のエラー予防アーキテクチャ

12. **error-hunter-README.md**
    - Error Hunterチームの概要とドキュメント

### 🔬 コード品質・レビューエージェント

13. **code-qa-reviewer.md**
    - 包括的なコードレビューと品質保証分析
    - セキュリティ、保守性、パフォーマンス評価
    - テスト戦略推奨

14. **review-agent.md**
    - コード品質判定
    - 静的解析、セキュリティスキャン
    - 品質スコアリング

15. **refactor-agent.md**
    - 機能を変更せずにコード品質を改善
    - 可読性、保守性、拡張性、テスト容易性の向上
    - SOLID原則に基づくリファクタリング

### 🚀 デプロイ・インフラエージェント

16. **deployment-agent.md**
    - CI/CDデプロイ自動化
    - Firebase自動デプロイ、ヘルスチェック
    - 自動ロールバック

17. **docker-builder.md**
    - アプリケーションのコンテナ化
    - Docker設定作成
    - 本番環境対応のコンテナ環境構築

### 📝 プロジェクト管理エージェント

18. **issue-agent.md**
    - Issue分析・ラベル管理
    - 組織設計原理65ラベル体系による自動分類

19. **pr-agent.md**
    - Pull Request自動作成
    - Conventional Commits準拠
    - Draft PR自動生成

### 🎯 統括・調整エージェント

20. **coordinator-agent.md**
    - タスク統括・並行実行制御
    - DAGベースの自律オーケストレーション

## 📊 カテゴリ別統計

- **開発・機能実装**: 2エージェント
- **デバッグ・エラー解決**: 10エージェント（Error Hunterチーム含む）
- **コード品質・レビュー**: 3エージェント
- **デプロイ・インフラ**: 2エージェント
- **プロジェクト管理**: 2エージェント
- **統括・調整**: 1エージェント

**総計: 21エージェント**

## 🔧 使用方法

各エージェントは、Claude Codeの`Task`ツールを使用して起動できます:

```python
# 例: デバッグエージェントの起動
Task(
    subagent_type="expert-debugger",
    description="テストエラーのデバッグ",
    prompt="test_api.pyのテストが失敗しています。根本原因を特定して修正してください。"
)
```

## 📖 推奨される使用順序

### 1. 新機能開発時
1. `autonomous-feature-builder` - 機能実装
2. `refactor-agent` - コード品質改善
3. `code-qa-reviewer` - レビュー実施
4. `pr-agent` - PR作成

### 2. エラー発生時
1. `error-hunter-coordinator` - エラー分析統括
2. Error Hunterチームによる段階的解決
3. `systematic-debugger` - 最終検証

### 3. デプロイ時
1. `docker-builder` - コンテナ化（必要な場合）
2. `deployment-agent` - 自動デプロイ

## 🎯 ベストプラクティス

- **並行実行**: 独立したタスクは複数エージェントを並行起動
- **段階的アプローチ**: 複雑な問題は小さなタスクに分割
- **適切なエージェント選択**: タスクの性質に最適なエージェントを選択
- **Error Hunterチーム**: 重大エラーはcoordinatorから起動

---

**最終更新**: 2025-11-02
**プロジェクト**: Kindle文字起こしツール
