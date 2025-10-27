---
description: エラーハンター君 - 5分でエラーを完全解決
---

# エラーハンター君起動

エラーハンター君の全自動エラー解決システムを起動します。

## 概要

このコマンドは、発生したエラーを**15分以内**に分析・修正・検証・再発防止まで完全自動で行います。

## 実行フロー

```
Phase 1: エラー情報収集 (対話形式)
  ↓
Phase 2: 症状分析 (2-3分)
  - SymptomAnalyzer: エラーログ解析・再現確認
  ↓
Phase 3: 真因特定 (4-5分)
  - RootCauseDetective: 根本原因の特定・証拠提示
  ↓
Phase 4: 修正パッチ生成 (2-3分)
  - SafePatcher: 最小差分修正・ロールバック手順
  ↓
Phase 5: テスト検証 (4-5分)
  - TestGuardian: テスト生成・品質ゲート実行
  ↓
Phase 6: 再発防止策設計 (2-3分)
  - PreventionArchitect: 5層防御設計
  ↓
Phase 7: 最終レポート生成 (1分)
```

## 収集する情報

### 必須項目
1. **症状**: どのような問題が発生していますか？
2. **エラーメッセージ**: エラーログやメッセージ
3. **再現手順**: エラーを再現する手順
4. **発生頻度**: always / sometimes / rarely
5. **緊急度**: P0-Critical / P1-High / P2-Medium / P3-Low

### 任意項目
6. **期待される動作**: 本来どうあるべきか
7. **スタックトレース**: 完全なスタックトレース
8. **直近の変更**: 最近のPRやコミット
9. **環境情報**: OS、Nodeバージョン等
10. **影響範囲**: 影響を受けるユーザー数

## 出力内容

### 最終レポート構成
```markdown
# エラーハンター君 完全解決レポート

## 🌟 素人向け説明（必須）
- **何が起きていたか**: 専門用語を使わず、誰でも理解できる言葉で問題を説明
- **何が原因だったか**: 技術的な詳細を避け、根本原因を分かりやすく説明
- **どう修正したか**: 修正内容を日常的な言葉で説明
- **今後どうなるか**: 修正後の動作と再発防止策を説明
- **影響範囲**: 誰に・どのくらい影響があったかを説明

---

## 技術者向け詳細

### 要約
- エラー種別
- 真因
- 修正内容
- テスト追加数
- カバレッジ変化
- 所要時間

## 修正ファイル
（修正したファイル一覧）

## 品質ゲート結果
✅ Lint: PASS
✅ Type Check: PASS
✅ Unit Tests: PASS
✅ E2E Tests: PASS
✅ Coverage: 80%+ PASS
✅ Security: PASS
✅ Performance: PASS

## 修正パッチ
（diff形式の修正コード）

## テストコード
（自動生成されたテストコード）

## 検証手順
（修正前後の動作確認コマンド）

## ロールバック手順
（3種類以上のロールバック方法）

## 再発防止策
（5層防御: 監視・静的解析・ランタイムガード・ドキュメント・プロセス）

## 次のアクション
1. [ ] 修正パッチの確認とマージ
2. [ ] PR作成: /pr-create
3. [ ] デプロイ: /deploy
4. [ ] 監視設定
5. [ ] ドキュメント更新
```

## 使用例

### 例1: TypeError の解決
```bash
症状: POST /api/users で 500 Internal Server Error
エラー: TypeError: Cannot read property 'id' of null
再現手順: curl -X POST http://localhost:3000/api/users -d '{"name":"test"}'
頻度: always
緊急度: P0-Critical

→ 15分後に完全解決レポート生成

【素人向け説明の例】
何が起きていたか:
新規会員登録ボタンを押すと、エラーが出て登録ができない状態でした。

何が原因だったか:
会員情報の一部（プロフィール欄）が空っぽのまま処理しようとしていたため、
システムが混乱してエラーになっていました。

どう修正したか:
プロフィール欄が空っぽの場合は、先に「プロフィールを入力してください」
というメッセージを表示するようにしました。

今後どうなるか:
これで、必要な情報が揃っているかを事前にチェックするようになり、
同じエラーは二度と起きません。

影響範囲:
過去2日間、新規登録しようとした約50人のユーザーに影響がありました。
既存ユーザーには影響ありません。
```

### 例2: ValidationError の解決
```bash
症状: Zod validation error で 400 エラー
エラー: Invalid input: expected string, received number
再現手順: POST /api/orders で quantity に文字列送信
頻度: sometimes
緊急度: P2-Medium

→ 15分後に解決
```

## 品質保証

エラーハンター君は以下を保証：

✅ **🌟 素人向け説明付き報告**（専門用語なし・誰でも理解できる）
✅ **15分以内**に完全解決
✅ **最小差分修正**（10行以内が理想）
✅ **カバレッジ80%以上**維持
✅ **全品質ゲートPASS**
✅ **ロールバック手順**必須提供
✅ **再発防止策**5層防御設計

## 個別エージェント実行

全体ではなく特定エージェントのみ実行する場合：

```bash
# 症状分析のみ
Task: .claude/agents/error-hunter/symptom-analyzer.md

# 真因特定のみ
Task: .claude/agents/error-hunter/root-cause-detective.md

# 修正パッチ生成のみ
Task: .claude/agents/error-hunter/safe-patcher.md

# テスト生成のみ
Task: .claude/agents/error-hunter/test-guardian.md

# 再発防止策設計のみ
Task: .claude/agents/error-hunter/prevention-architect.md
```

## トラブルシューティング

### エージェントが起動しない
```bash
# エージェント定義を確認
ls -la .claude/agents/error-hunter/

# 必要なファイル:
# - coordinator.md
# - symptom-analyzer.md
# - root-cause-detective.md
# - safe-patcher.md
# - test-guardian.md
# - prevention-architect.md
```

### 分析が途中で止まる
```bash
# ログを確認
cat logs/error-hunter.log

# 個別エージェント実行でデバッグ
```

## 関連コマンド

- `/test` - テスト実行
- `/verify` - システム動作確認
- `/security-scan` - セキュリティスキャン
- `/deploy` - デプロイ実行

---

**エラーハンター君 - 5分でエラーを完全解決 🔍**
