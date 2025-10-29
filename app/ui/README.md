# Kindle OCR - Streamlit UI

Kindle書籍自動文字起こしシステムのWeb UIインターフェース

## 📚 概要

Streamlit UIは、FastAPIバックエンドと連携してKindle書籍のOCR処理を簡単に実行できるWebインターフェースを提供します。

## 🎯 主な機能

### 1. **Home (ホーム)** - `Home.py`
- システム概要とステータス表示
- クイック統計（総ジョブ数、OCR処理ページ数、成功率）
- 最近のジョブ一覧
- システムヘルスチェック（API、Database、Redis）

### 2. **📤 Upload (手動OCR)** - `pages/1_📤_Upload.py`
- 画像ファイルのアップロード (.png, .jpg, .jpeg)
- 書籍タイトルとページ番号の入力
- リアルタイムOCR処理
- OCR結果の表示（テキスト、信頼度スコア）
- 抽出テキストのダウンロード

### 3. **🤖 Auto Capture (自動キャプチャ)** - `pages/2_🤖_Auto_Capture.py`
- Amazon認証情報の入力
- Kindle Cloud Reader URLの入力
- 最大ページ数とヘッドレスモードの設定
- リアルタイム進捗表示
- キャプチャ中のステータス更新
- OCR結果のプレビュー

### 4. **📊 Jobs (ジョブ管理)** - `pages/3_📊_Jobs.py`
- 全ジョブの一覧表示
- ステータスフィルター（pending, processing, completed, failed）
- ジョブ詳細の表示
- OCR結果の確認
- CSVエクスポート機能

## 🚀 起動方法

### 前提条件

1. **FastAPIバックエンドが起動していること**
   ```bash
   uvicorn app.main:app --reload
   ```

2. **必要なパッケージがインストール済み**
   ```bash
   pip install streamlit requests pandas
   ```

### UIの起動

プロジェクトルートディレクトリから以下のコマンドを実行：

```bash
streamlit run app/ui/Home.py
```

デフォルトでブラウザが自動的に開き、`http://localhost:8501` でUIにアクセスできます。

### 環境変数

`.env` ファイルまたは環境変数で以下を設定できます：

```bash
# FastAPI バックエンドのURL（デフォルト: http://localhost:8000）
API_BASE_URL=http://localhost:8000
```

## 📁 ディレクトリ構造

```
app/ui/
├── Home.py                          # メインページ（ホーム）
├── pages/
│   ├── 1_📤_Upload.py              # 手動OCRアップロード
│   ├── 2_🤖_Auto_Capture.py       # 自動キャプチャ
│   └── 3_📊_Jobs.py                # ジョブ管理
├── utils/
│   ├── __init__.py
│   └── api_client.py               # API通信ユーティリティ
├── __init__.py
└── README.md                        # このファイル
```

## 🔧 API Client (`utils/api_client.py`)

FastAPI バックエンドとの通信を行うユーティリティ関数を提供します。

### 主な関数

#### `upload_image(file_data, filename, book_title, page_num)`
画像をアップロードしてOCR処理を実行

**パラメータ:**
- `file_data` (bytes): 画像ファイルのバイトデータ
- `filename` (str): ファイル名
- `book_title` (str): 書籍タイトル
- `page_num` (int): ページ番号

**戻り値:** OCR結果 (dict)
```python
{
    "job_id": "550e8400-e29b-41d4-a716-446655440000",
    "book_title": "サンプル書籍",
    "page_num": 1,
    "text": "抽出されたテキスト...",
    "confidence": 0.95
}
```

#### `start_auto_capture(email, password, book_url, book_title, max_pages, headless)`
自動キャプチャを開始

**パラメータ:**
- `email` (str): AmazonアカウントのEメール
- `password` (str): Amazonパスワード
- `book_url` (str): Kindle Cloud Reader URL
- `book_title` (str): 書籍タイトル（デフォルト: "Untitled"）
- `max_pages` (int): 最大ページ数（デフォルト: 50）
- `headless` (bool): ヘッドレスモード（デフォルト: True）

**戻り値:** ジョブ開始レスポンス (dict)
```python
{
    "job_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "pending",
    "message": "自動キャプチャジョブを開始しました。..."
}
```

#### `get_job_status(job_id)`
ジョブのステータスを取得

**パラメータ:**
- `job_id` (str): ジョブID (UUID)

**戻り値:** ジョブステータス (dict)
```python
{
    "job_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "processing",
    "progress": 50,
    "pages_captured": 25,
    "total_pages": 50,
    "error_message": null,
    "ocr_results": [...],
    "created_at": "2025-10-28T10:30:00",
    "completed_at": null
}
```

#### `list_jobs(limit=10)`
ジョブの一覧を取得

**パラメータ:**
- `limit` (int): 取得件数（デフォルト: 10）

**戻り値:** ジョブリスト (list[dict])

#### `get_health()`
システムのヘルスチェック

**戻り値:** ヘルスチェック結果 (dict)
```python
{
    "status": "healthy",
    "database": "postgresql",
    "pool_size": 10,
    "checked_out": 2
}
```

## 🎨 UI 機能詳細

### ホームページ (Home.py)

**表示内容:**
- システム概要
- クイック統計
  - 総ジョブ数
  - OCR処理ページ数
  - 完了ジョブ数
  - 成功率
- 最近のジョブ一覧（最新10件）
- システムヘルスチェック
- クイックスタートガイド

**操作:**
- リフレッシュボタンでデータ更新
- ページ間のナビゲーション

### Upload ページ (1_📤_Upload.py)

**機能:**
- ドラッグ&ドロップまたはクリックで画像アップロード
- 画像プレビュー表示
- 書籍タイトルとページ番号の入力
- OCR処理の実行
- 結果表示（テキスト、信頼度スコア）
- テキストのダウンロード

**バリデーション:**
- ファイル形式チェック (.png, .jpg, .jpeg)
- ファイルサイズチェック (最大10MB)
- 必須項目チェック（書籍タイトル）

**UI要素:**
- ファイルアップローダー
- テキスト入力フィールド
- 数値入力フィールド
- 進捗インジケーター
- 結果表示エリア

### Auto Capture ページ (2_🤖_Auto_Capture.py)

**機能:**
- Amazon認証情報の入力（Email, Password）
- Kindle Cloud Reader URLの入力
- 書籍タイトルの入力
- 最大ページ数のスライダー（1-100）
- ヘッドレスモードのチェックボックス
- リアルタイム進捗表示
- 自動ステータス更新（5秒ごと）
- OCR結果のタブ表示

**セッション管理:**
- `capture_job_id`: 実行中のジョブID
- `capture_running`: キャプチャ実行中フラグ
- `last_progress`: 前回の進捗率

**状態遷移:**
1. フォーム表示
2. キャプチャ開始
3. ステータス表示（自動更新）
4. 完了または失敗

### Jobs ページ (3_📊_Jobs.py)

**機能:**
- 全ジョブの一覧表示
- ステータスフィルター
  - すべて
  - pending
  - processing
  - completed
  - failed
- 表示件数の調整（5-100件）
- ジョブ詳細の展開表示
- OCR結果の取得と表示
- CSVエクスポート

**統計情報:**
- 総ジョブ数
- 完了数
- 処理中数
- 失敗数

**エクスポート:**
- CSV形式でジョブデータをダウンロード
- ファイル名: `kindle_ocr_jobs_YYYYMMDD_HHMMSS.csv`

## 🔒 セキュリティ考慮事項

1. **パスワード入力**
   - `type="password"` で入力内容を隠蔽
   - セッション終了後は自動クリア

2. **API通信**
   - HTTPSの使用を推奨（本番環境）
   - エラーメッセージに機密情報を含めない

3. **入力バリデーション**
   - ファイルサイズ制限
   - ファイル形式制限
   - 必須項目チェック

## 🐛 トラブルシューティング

### UIが起動しない

```bash
# Streamlitがインストールされているか確認
pip show streamlit

# インストールされていない場合
pip install streamlit
```

### API接続エラー

1. FastAPIサーバーが起動しているか確認
   ```bash
   uvicorn app.main:app --reload
   ```

2. API_BASE_URLが正しいか確認
   ```bash
   echo $API_BASE_URL  # デフォルト: http://localhost:8000
   ```

3. ファイアウォールの設定を確認

### 画像アップロードエラー

1. ファイル形式を確認（.png, .jpg, .jpeg のみ）
2. ファイルサイズを確認（最大10MB）
3. 画像ファイルが破損していないか確認

### 自動キャプチャが失敗する

1. Amazon認証情報を確認
2. Kindle Cloud Reader URLが正しいか確認
3. ヘッドレスモードをOFFにしてブラウザの動作を確認
4. ネットワーク接続を確認

## 📊 パフォーマンス

- **ページロード時間**: < 1秒
- **API レスポンス時間**: 1-5秒（OCR処理）
- **自動更新間隔**: 5秒（処理中のみ）
- **同時接続数**: 制限なし（FastAPIが処理）

## 🔄 更新履歴

### v1.0.0 (Phase 1-6 MVP)
- ホームページの実装
- 手動OCRアップロード機能
- 自動キャプチャ機能
- ジョブ管理機能
- CSVエクスポート機能
- リアルタイムステータス更新

## 📝 今後の拡張予定

- [ ] ユーザー認証機能
- [ ] ジョブの編集・削除機能
- [ ] OCR結果の編集機能
- [ ] 書籍ごとのグループ化
- [ ] 高度な検索機能
- [ ] ダークモード対応
- [ ] 多言語対応

## 🤝 貢献

バグ報告や機能要望は、GitHubのIssueでお知らせください。

## 📄 ライセンス

MIT License

## 👨‍💻 作者

Kindle OCR Development Team
