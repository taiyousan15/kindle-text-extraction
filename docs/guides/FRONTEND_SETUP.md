# Kindle OCR - Frontend Setup Guide

モダンなReact/Next.jsフロントエンドの完全セットアップガイド

## 実装完了内容

### 技術スタック

**フロントエンド:**
- Next.js 14 (App Router)
- React 18
- TypeScript
- Tailwind CSS
- React Query
- Zustand

**UIコンポーネント:**
- Radix UI (アクセシブルなプリミティブ)
- Lucide React (アイコン)
- Sonner (トースト通知)
- react-dropzone (ファイルアップロード)

### 実装されたページ

1. **ダッシュボード (/)** ✅
   - システム概要と統計
   - 最近のジョブ表示
   - クイックアクションボタン
   - ヘルスステータス監視

2. **OCRアップロード (/upload)** ✅
   - ドラッグ&ドロップファイルアップロード
   - 画像プレビュー
   - リアルタイムOCR処理
   - テキスト抽出結果表示
   - 抽出テキストダウンロード

3. **RAG検索 (/rag)** ✅
   - 自然言語質問入力
   - AI生成回答
   - ソース引用表示
   - 書籍フィルタリング

4. **ジョブ管理 (/jobs)** ✅
   - 全ジョブ一覧
   - ステータスフィルター
   - リアルタイム進捗表示
   - CSVエクスポート

### プロジェクト構造

```
frontend/
├── src/
│   ├── app/
│   │   ├── page.tsx              # ダッシュボード
│   │   ├── upload/page.tsx       # OCRアップロード
│   │   ├── rag/page.tsx          # RAG検索
│   │   ├── jobs/page.tsx         # ジョブ管理
│   │   ├── layout.tsx            # ルートレイアウト
│   │   └── globals.css           # グローバルスタイル
│   ├── components/
│   │   ├── layout/
│   │   │   ├── sidebar.tsx       # サイドバーナビゲーション
│   │   │   ├── header.tsx        # ヘッダー
│   │   │   └── main-layout.tsx   # メインレイアウト
│   │   ├── dashboard/
│   │   │   ├── stats-card.tsx    # 統計カード
│   │   │   └── recent-jobs.tsx   # 最近のジョブ
│   │   ├── ui/                   # 再利用可能UIコンポーネント
│   │   │   ├── button.tsx
│   │   │   └── card.tsx
│   │   └── providers.tsx         # アプリプロバイダー
│   ├── lib/
│   │   ├── api.ts                # APIクライアント
│   │   └── utils.ts              # ユーティリティ関数
│   └── types/
│       └── index.ts              # TypeScript型定義
├── public/                       # 静的ファイル
├── package.json
├── tsconfig.json
├── tailwind.config.ts
├── next.config.mjs
├── setup.sh                      # セットアップスクリプト
└── README.md
```

## クイックスタート

### 前提条件

- Node.js 18以上
- npm または yarn または pnpm
- FastAPIバックエンドが http://localhost:8000 で起動していること

### インストール

```bash
# フロントエンドディレクトリに移動
cd frontend

# セットアップスクリプトを実行
./setup.sh

# または手動でインストール
npm install
```

### 環境変数の設定

`.env.local` ファイルが自動作成されます:

```env
# API設定
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000

# アプリケーション設定
NEXT_PUBLIC_APP_NAME="Kindle OCR"
NEXT_PUBLIC_APP_VERSION="2.0.0"
```

### 開発サーバーの起動

```bash
# 開発モードで起動
npm run dev
```

ブラウザで http://localhost:3000 を開きます。

### 本番ビルド

```bash
# 本番用ビルド
npm run build

# 本番サーバー起動
npm run start
```

## 機能詳細

### ダッシュボード

**主な機能:**
- 総ジョブ数、完了数、処理中数の統計表示
- OCR処理済みページ数の表示
- 最近の5件のジョブをリアルタイム表示
- クイックアクションボタン（アップロード、自動キャプチャ、RAG検索）
- システムヘルスステータス（30秒ごとに自動更新）

**使用コンポーネント:**
- `StatsCard` - 統計情報カード
- `RecentJobs` - 最近のジョブリスト
- React Query - データフェッチングと自動更新

### OCRアップロード

**主な機能:**
- ドラッグ&ドロップまたはクリックでファイルアップロード
- 画像プレビュー表示
- ファイルサイズとバリデーション（最大10MB）
- リアルタイムOCR処理
- 信頼度スコア表示（色分け）
- 抽出テキストの表示と編集
- テキストファイルダウンロード

**技術仕様:**
- `react-dropzone` - ファイルアップロード
- React Query Mutation - OCR処理
- Sonner - トースト通知

### RAG検索

**主な機能:**
- 自然言語での質問入力
- 書籍タイトルでフィルタリング（オプション）
- AI生成の回答表示
- ソース引用表示（ページ番号、信頼度付き）
- リアルタイム処理状態表示

**APIエンドポイント:**
- `POST /api/v1/rag/ask`

### ジョブ管理

**主な機能:**
- 全ジョブのリスト表示
- ステータスフィルター（すべて、待機中、処理中、完了、失敗）
- 表示件数調整（10/20/50/100件）
- リアルタイム進捗表示（5秒ごとに自動更新）
- CSVエクスポート機能
- ジョブ詳細表示

**統計情報:**
- 総ジョブ数
- 完了数
- 処理中数
- 失敗数

## API統合

### APIクライアント (`src/lib/api.ts`)

すべてのAPI通信を管理:

```typescript
// ヘルスチェック
const health = await api.health();

// OCRアップロード
const result = await api.uploadImage(file, bookTitle, pageNum);

// ジョブ取得
const jobs = await api.listJobs(10);

// RAG質問
const answer = await api.askQuestion({ question, book_title });
```

### React Queryの使用

効率的なデータフェッチング:

```typescript
// 自動リフェッチ
const { data, isLoading } = useQuery(
  "jobs",
  () => api.listJobs(10),
  {
    refetchInterval: 5000, // 5秒ごと
  }
);

// ミューテーション
const mutation = useMutation(
  (data) => api.uploadImage(data),
  {
    onSuccess: () => toast.success("成功!"),
    onError: (error) => toast.error(error.message),
  }
);
```

## スタイリング

### Tailwind CSS

ユーティリティファーストのCSSフレームワーク:

```tsx
<div className="flex items-center space-x-4 rounded-lg border p-4">
  <h2 className="text-2xl font-bold">タイトル</h2>
</div>
```

### ダークモード

`next-themes`を使用したテーマ切り替え:

```tsx
import { useTheme } from "next-themes";

const { theme, setTheme } = useTheme();
setTheme("dark"); // または "light"
```

### カスタムカラー

`tailwind.config.ts` と `globals.css` で定義:

```css
--primary: 221.2 83.2% 53.3%;        /* ブルー */
--secondary: 210 40% 96.1%;          /* ライトグレー */
--destructive: 0 84.2% 60.2%;        /* レッド */
```

## 開発ガイド

### スクリプト

```bash
# 開発サーバー
npm run dev              # http://localhost:3000

# 本番ビルド
npm run build            # Next.jsビルド
npm run start            # 本番サーバー起動

# コード品質
npm run lint             # ESLintチェック
npm run type-check       # TypeScriptコンパイラチェック
```

### 新しいページの追加

1. `src/app/新しいページ/page.tsx` を作成
2. `MainLayout` でラップ
3. `src/components/layout/sidebar.tsx` にナビゲーションリンクを追加

例:

```tsx
// src/app/my-page/page.tsx
import { MainLayout } from "@/components/layout/main-layout";

export default function MyPage() {
  return (
    <MainLayout>
      <h1>新しいページ</h1>
    </MainLayout>
  );
}
```

### 新しいAPIエンドポイントの追加

`src/lib/api.ts` に関数を追加:

```typescript
export const api = {
  // 既存の関数...

  myNewEndpoint: async (data: any): Promise<any> => {
    const response = await apiClient.post("/api/v1/my-endpoint", data);
    return response.data;
  },
};
```

## デプロイ

### Docker

```dockerfile
FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build
EXPOSE 3000
CMD ["npm", "start"]
```

ビルド & 実行:

```bash
docker build -t kindle-ocr-frontend .
docker run -p 3000:3000 -e NEXT_PUBLIC_API_BASE_URL=http://localhost:8000 kindle-ocr-frontend
```

### Vercel

```bash
# Vercelにデプロイ
npm install -g vercel
vercel

# 環境変数を設定
vercel env add NEXT_PUBLIC_API_BASE_URL
```

## トラブルシューティング

### API接続エラー

**問題:** FastAPIバックエンドに接続できない

**解決方法:**
1. バックエンドが起動しているか確認: `curl http://localhost:8000/health`
2. `.env.local` の `NEXT_PUBLIC_API_BASE_URL` を確認
3. FastAPIのCORS設定を確認

### ビルドエラー

**問題:** TypeScriptエラーでビルドが失敗

**解決方法:**
```bash
npm run type-check  # 型エラーをチェック
npm run lint        # リントエラーをチェック
```

### スタイルが適用されない

**問題:** Tailwindスタイルが機能しない

**解決方法:**
1. `tailwind.config.ts` のパス設定を確認
2. `globals.css` が `@tailwind` ディレクティブをインポートしているか確認
3. 開発サーバーを再起動

## パフォーマンス最適化

- **コード分割:** ルートベースの自動分割
- **画像最適化:** Next.js Imageコンポーネント
- **遅延読み込み:** コンポーネントのオンデマンドロード
- **キャッシング:** React Queryキャッシュ管理

## セキュリティ

- **XSS対策:** Reactの自動エスケープ
- **CSRF対策:** SameSite Cookie
- **環境変数:** クライアントサイド変数は `NEXT_PUBLIC_` プレフィックス必須

## 今後の拡張

### 追加予定の機能

1. **自動キャプチャページ** - Kindle Cloud Readerからの自動ページキャプチャ
2. **ナレッジベースページ** - 抽出した知識の一覧と検索
3. **ユーザー認証** - ログイン/ログアウト機能
4. **リアルタイム通知** - WebSocketによるプッシュ通知
5. **高度なフィルタリング** - 日付範囲、書籍カテゴリなど
6. **データビジュアライゼーション** - グラフとチャート

### 実装方法

自動キャプチャページの例:

```tsx
// src/app/capture/page.tsx
import { MainLayout } from "@/components/layout/main-layout";

export default function CapturePage() {
  const [isCapturing, setIsCapturing] = useState(false);

  const startCapture = useMutation(
    (data) => api.startCapture(data),
    {
      onSuccess: () => {
        setIsCapturing(true);
        toast.success("キャプチャ開始!");
      },
    }
  );

  return (
    <MainLayout>
      {/* キャプチャUIの実装 */}
    </MainLayout>
  );
}
```

## サポート

- **ドキュメント:** [メインREADME](../README.md)
- **バックエンドAPI:** http://localhost:8000/docs
- **Issue報告:** GitHub Issues

## 貢献

1. フィーチャーブランチを作成
2. 変更を実装
3. `npm run type-check` と `npm run lint` を実行
4. プルリクエストを提出

## ライセンス

MIT License - LICENSEファイルを参照

---

**Next.js 14 & React 18で構築** | **Kindle OCR Frontend v2.0.0**
