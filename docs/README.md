# Kindle文字起こしツール - ドキュメント索引

このディレクトリには、プロジェクトの全ドキュメントが整理されています。

## 📂 ディレクトリ構造

```
docs/
├── README.md (このファイル)
├── architecture/     # アーキテクチャ・設計書
├── guides/          # ガイド・リファレンス
└── reports/         # 実装レポート・完了報告
```

---

## 🏗️ アーキテクチャ・設計書 (architecture/)

### 要件定義
- **Kindle文字起こし要件定義書.md** - 初版要件定義書
- **Kindle文字起こし要件定義書_v2_改善版.md** - 改善版要件定義書
- **Kindle文字起こし要件定義書_v3_ローカル版.md** - ローカル版要件定義書

### アーキテクチャ
- **ARCHITECTURE_DIAGRAM.md** - システムアーキテクチャ図と技術スタック
- **DEVELOPMENT_PLAN.md** - 開発計画とフェーズ構成

---

## 📖 ガイド・リファレンス (guides/)

### クイックスタート
- **QUICK_START.md** - プロジェクト全体のクイックスタートガイド
- **QUICKSTART_CAPTURE.md** - 自動キャプチャ機能のクイックスタート
- **QUICKSTART_OCR.md** - OCR機能のクイックスタート
- **QUICKSTART_RAG.md** - RAG機能のクイックスタート
- **QUICKSTART_UI.md** - UI機能のクイックスタート

### セットアップ
- **FRONTEND_SETUP.md** - フロントエンド(Streamlit)セットアップガイド
- **MIYABI_SETUP.md** - Miyabiエージェントシステムセットアップ

### CI/CDガイド
- **CI_CD_GUIDE.md** - CI/CD詳細ガイド
- **CI_CD_QUICK_REFERENCE.md** - CI/CDクイックリファレンス

### その他リファレンス
- **INDEX_QUICK_REFERENCE.md** - データベースインデックスクイックリファレンス
- **RATE_LIMITING_QUICK_REF.md** - レート制限クイックリファレンス
- **NEXT_STEPS.md** - 今後の開発ステップ
- **QUICK_TROUBLESHOOTING.md** - トラブルシューティングガイド

---

## 📊 実装レポート・完了報告 (reports/)

### 完了報告
- **FINAL_COMPLETION_REPORT.md** - 最終完了報告書
- **FINAL_SESSION_SUMMARY.md** - 最終セッションサマリー
- **IMPLEMENTATION_COMPLETE.md** - 実装完了報告
- **IMPLEMENTATION_SUMMARY.md** - 実装サマリー

### フェーズ別レポート
- **PHASE1_MVP_COMPLETE.md** - Phase 1 MVP完了報告
- **PHASE1-3_IMPLEMENTATION.md** - Phase 1-3実装報告
- **PHASE2_SUMMARY.md** - Phase 2サマリー
- **PHASE3_SUMMARY.md** - Phase 3サマリー
- **PHASE3_QUICKSTART.md** - Phase 3クイックスタート
- **PHASE4_KNOWLEDGE_EXTRACTION.md** - Phase 4知識抽出実装
- **PHASE5-7_IMPLEMENTATION.md** - Phase 5-7実装報告
- **PHASE_1-4_IMPLEMENTATION_SUMMARY.md** - Phase 1-4実装サマリー
- **PHASE_5_6_STATUS_REPORT.md** - Phase 5-6ステータスレポート
- **PHASE_1-6_UI_IMPLEMENTATION.md** - Phase 1-6 UI実装報告
- **PHASE_8_SUMMARY.md** - Phase 8サマリー
- **PHASE_9_CI_CD_COMPLETE.md** - Phase 9 CI/CD完了報告

### 機能別実装レポート
- **OCR_REBUILD_SUMMARY.md** - 🔥 **OCRシステム完全再構築レポート（最新・重要）**
- **OCR_PAGE_DETECTION_IMPLEMENTATION.md** - OCRページ検出実装
- **RAG_IMPLEMENTATION.md** - RAG実装レポート
- **RATE_LIMITING_IMPLEMENTATION.md** - レート制限実装レポート
- **FRONTEND_IMPLEMENTATION_COMPLETE.md** - フロントエンド実装完了報告

### バグ修正・デバッグレポート
- **BUG_FIX_REPORT.md** - バグ修正レポート
- **DEBUGGING_REPORT.md** - デバッグレポート
- **DOWNLOAD_FIX_SUCCESS.md** - ダウンロード機能修正成功報告
- **DOWNLOAD_FIX_VERIFICATION.md** - ダウンロード機能検証報告

### CI/CD・デプロイレポート
- **CI_CD_IMPLEMENTATION_COMPLETE.md** - CI/CD実装完了報告
- **DEPLOYMENT.md** - デプロイメントガイド
- **DEPLOYMENT_READY_REPORT.md** - デプロイ準備完了報告

### レビュー・品質管理
- **PRODUCTION_READINESS_VERDICT.md** - 本番環境準備度判定
- **SYSTEM_REVIEW_AND_IMPROVEMENTS.md** - システムレビューと改善提案
- **PERFORMANCE_INDEXES_REPORT.md** - パフォーマンスインデックスレポート

---

## 🔥 最新の重要ドキュメント

### OCRシステム完全再構築（2025-11-01）
📄 **reports/OCR_REBUILD_SUMMARY.md**
- ユーザーフィードバックに基づく完全再構築
- 高精度OCR前処理パイプライン導入
- ヘッダー/フッター除去実装（上下10%）
- テキストクリーニング（ページ番号、書籍タイトル除去）
- 79%のジャンクテキスト削減達成
- テスト結果: 書籍タイトル・ページ番号の完全除去確認

### エージェントシステム
📄 **.claude/agents/AGENTS_INDEX.md**
- 21個の専門エージェント一覧
- カテゴリ別分類（開発、デバッグ、品質管理、デプロイ、プロジェクト管理）
- 使用方法とベストプラクティス

---

## 📋 プロジェクトステータス

### ✅ 完了フェーズ
- Phase 1-3: MVP実装（OCR、自動キャプチャ、基本UI）
- Phase 4: 知識抽出・要約機能
- Phase 5-7: フロントエンドUI実装
- Phase 8: セキュリティ・認証システム
- Phase 9: CI/CD自動化
- **OCRシステム完全再構築**: ヘッダー/フッター除去、高精度前処理

### 🔄 現在のステータス
- システム全体: **本番環境準備完了**
- OCRシステム: **完全再構築完了（ユーザーテスト待ち）**
- CI/CD: **自動デプロイ稼働中**

---

## 🚀 次のステップ

1. **OCRシステム検証** - 新しい自動キャプチャジョブでテスト実施
2. **本番環境デプロイ** - 最終チェック後にデプロイ
3. **セキュリティ監査** - 本番環境前の最終セキュリティチェック

---

**最終更新**: 2025-11-02
**プロジェクト**: Kindle文字起こしツール
**バージョン**: v1.0 (Production Ready)
