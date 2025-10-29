#!/bin/bash

# Kindle OCR - Streamlit UI Startup Script
# このスクリプトはStreamlit UIを起動します

set -e

echo "🚀 Kindle OCR - Streamlit UI を起動します..."
echo ""

# プロジェクトルートに移動
cd "$(dirname "$0")"

# 環境変数の確認
if [ -f .env ]; then
    echo "✅ .env ファイルを読み込んでいます..."
    export $(cat .env | grep -v '^#' | xargs)
else
    echo "⚠️  .env ファイルが見つかりません（オプション）"
fi

# API_BASE_URLのデフォルト値
if [ -z "$API_BASE_URL" ]; then
    export API_BASE_URL="http://localhost:8000"
    echo "📡 API_BASE_URL: $API_BASE_URL (デフォルト)"
else
    echo "📡 API_BASE_URL: $API_BASE_URL"
fi

# FastAPI サーバーの起動確認
echo ""
echo "🔍 FastAPI サーバーの起動を確認しています..."
if curl -s "$API_BASE_URL/health" > /dev/null 2>&1; then
    echo "✅ FastAPI サーバーが起動しています"
else
    echo "⚠️  FastAPI サーバーが起動していないようです"
    echo "   以下のコマンドで起動してください:"
    echo "   uvicorn app.main:app --reload"
    echo ""
    read -p "それでも続行しますか？ (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ UIの起動をキャンセルしました"
        exit 1
    fi
fi

# Streamlit の起動
echo ""
echo "🎨 Streamlit UI を起動します..."
echo "   URL: http://localhost:8501"
echo ""
echo "💡 Ctrl+C で終了できます"
echo ""

streamlit run app/ui/Home.py \
    --server.port 8501 \
    --server.address localhost \
    --browser.gatherUsageStats false

echo ""
echo "👋 Streamlit UI を終了しました"
