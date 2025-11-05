#!/bin/bash
# =========================================================
# T-Max Work3 Full-Auto Pipeline Launcher
# =========================================================

set -e

REPO_PATH="$(cd "$(dirname "$0")/.." && pwd)"
DEPLOY_TARGET="${DEPLOY_TARGET:-vercel}"
EMAIL_REPORT="${EMAIL_REPORT:-}"

echo "🚀 T-Max Work3 Full-Auto Pipeline Launcher"
echo "=" | tr ' ' '=' | head -c 60; echo
echo "Repository: $REPO_PATH"
echo "Deploy Target: $DEPLOY_TARGET"
echo "=" | tr ' ' '=' | head -c 60; echo

# Python実行
cd "$REPO_PATH"
python3 tmax_work3/agents/coordinator.py \
  --repo "$REPO_PATH" \
  --target "$DEPLOY_TARGET" \
  --auto

echo ""
echo "✅ Pipeline execution completed"
echo "📊 Check reports at: tmax_work3/reports/"
echo "📋 Check logs at: tmax_work3/logs/"
echo ""
echo "🖥️  To view tmux session:"
echo "   tmux attach -t TMAX_FULLAUTO"
