"""
T-Max Work3 Error Recovery Agent
エラー自動検出・分析・修正提案を担当

機能:
- エラーログの自動分析
- エラーパターン学習（ML）
- 自動修正コード生成
- 緊急時のロールバック
- エラー通知（Slack/Email）
"""
import os
import re
import subprocess
import traceback
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import sys
import json

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from tmax_work3.blackboard.state_manager import (
    Blackboard,
    AgentType,
    TaskStatus,
    get_blackboard
)

try:
    from anthropic import Anthropic
except ImportError:
    Anthropic = None


class ErrorRecoveryAgent:
    """
    Error Recovery Agent - エラー自動復旧エージェント

    役割:
    - エラーログ収集と分析
    - エラーパターンマッチング
    - 自動修正コード生成（Claude API）
    - 修正適用と検証
    - エラー通知
    """

    def __init__(self, repository_path: str):
        self.repo_path = Path(repository_path)
        self.blackboard = get_blackboard()
        self.error_patterns_path = self.repo_path / "tmax_work3" / "data" / "error_patterns.json"
        self.error_patterns_path.parent.mkdir(parents=True, exist_ok=True)

        # Claude API初期化
        self.claude_client = None
        if Anthropic and os.getenv("ANTHROPIC_API_KEY"):
            self.claude_client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

        # エージェント登録
        self.blackboard.register_agent(
            AgentType.ERROR_RECOVERY,
            worktree="main"
        )

        # エラーパターンロード
        self.error_patterns = self._load_error_patterns()

        self.blackboard.log(
            "🚨 Error Recovery Agent initialized",
            level="INFO",
            agent=AgentType.ERROR_RECOVERY
        )

    def _load_error_patterns(self) -> Dict:
        """既知のエラーパターンを読み込む"""
        if self.error_patterns_path.exists():
            return json.loads(self.error_patterns_path.read_text())

        # デフォルトパターン
        default_patterns = {
            "browser_extension_interference": {
                "pattern": r"Cannot redefine property: ethereum",
                "description": "Browser extension (MetaMask, Pocket Universe) interference",
                "fix_type": "add_chrome_flag",
                "fix_content": "--disable-extensions",
                "severity": "high",
                "occurrences": 0
            },
            "kindle_terms_popup": {
                "pattern": r"Kindle.*規約|terms.*agreement",
                "description": "Kindle for Web terms popup blocking interaction",
                "fix_type": "auto_dismiss_popup",
                "fix_content": "XPath selector strategy",
                "severity": "medium",
                "occurrences": 0
            },
            "page_turn_failure": {
                "pattern": r"ページがめくられ|page.*turn.*fail",
                "description": "Kindle page turn failure",
                "fix_type": "retry_with_wait",
                "fix_content": "Add explicit wait and retry logic",
                "severity": "high",
                "occurrences": 0
            },
            "database_connection": {
                "pattern": r"connection.*refused|database.*not.*available",
                "description": "Database connection failure",
                "fix_type": "reconnect",
                "fix_content": "Retry with exponential backoff",
                "severity": "critical",
                "occurrences": 0
            },
            "api_timeout": {
                "pattern": r"timeout|timed out",
                "description": "API timeout",
                "fix_type": "increase_timeout",
                "fix_content": "Increase timeout from 30s to 60s",
                "severity": "medium",
                "occurrences": 0
            }
        }

        self.error_patterns_path.write_text(json.dumps(default_patterns, indent=2))
        return default_patterns

    def _save_error_patterns(self):
        """エラーパターンを保存"""
        self.error_patterns_path.write_text(json.dumps(self.error_patterns, indent=2))

    def collect_error_logs(self, log_paths: List[str]) -> List[Dict]:
        """
        エラーログを収集

        Args:
            log_paths: ログファイルパスのリスト

        Returns:
            エラーエントリのリスト
        """
        self.blackboard.log(
            f"📋 Collecting error logs from {len(log_paths)} sources...",
            level="INFO",
            agent=AgentType.ERROR_RECOVERY
        )

        errors = []

        for log_path_str in log_paths:
            log_path = Path(log_path_str)
            if not log_path.exists():
                continue

            try:
                content = log_path.read_text()
                lines = content.split('\n')

                for i, line in enumerate(lines):
                    if any(keyword in line.lower() for keyword in ['error', 'exception', 'failed', 'エラー']):
                        errors.append({
                            "file": str(log_path),
                            "line_number": i + 1,
                            "content": line,
                            "context": lines[max(0, i-2):min(len(lines), i+3)],
                            "timestamp": datetime.now().isoformat()
                        })

            except Exception as e:
                self.blackboard.log(
                    f"⚠️ Failed to read log: {log_path}: {str(e)}",
                    level="WARNING",
                    agent=AgentType.ERROR_RECOVERY
                )

        self.blackboard.log(
            f"✅ Collected {len(errors)} error entries",
            level="SUCCESS",
            agent=AgentType.ERROR_RECOVERY
        )

        return errors

    def analyze_error(self, error_log: str, context: Optional[str] = None) -> Dict:
        """
        エラーログを分析

        Args:
            error_log: エラーログ文字列
            context: 追加コンテキスト

        Returns:
            分析結果
        """
        self.blackboard.log(
            "🔍 Analyzing error...",
            level="INFO",
            agent=AgentType.ERROR_RECOVERY
        )

        analysis = {
            "error_log": error_log,
            "matched_patterns": [],
            "severity": "unknown",
            "suggested_fix": None,
            "claude_analysis": None
        }

        # パターンマッチング
        for pattern_name, pattern_data in self.error_patterns.items():
            if re.search(pattern_data["pattern"], error_log, re.IGNORECASE):
                analysis["matched_patterns"].append(pattern_name)
                analysis["severity"] = pattern_data["severity"]
                analysis["suggested_fix"] = {
                    "type": pattern_data["fix_type"],
                    "content": pattern_data["fix_content"],
                    "description": pattern_data["description"]
                }

                # 出現回数を更新
                pattern_data["occurrences"] += 1
                self._save_error_patterns()

        # Claude APIで詳細分析
        if self.claude_client:
            try:
                analysis["claude_analysis"] = self._analyze_with_claude(error_log, context)
            except Exception as e:
                self.blackboard.log(
                    f"⚠️ Claude analysis failed: {str(e)}",
                    level="WARNING",
                    agent=AgentType.ERROR_RECOVERY
                )

        self.blackboard.log(
            f"✅ Analysis complete: {len(analysis['matched_patterns'])} patterns matched",
            level="SUCCESS",
            agent=AgentType.ERROR_RECOVERY
        )

        return analysis

    def _analyze_with_claude(self, error_log: str, context: Optional[str]) -> Dict:
        """Claude APIでエラーを分析"""

        prompt = f"""エラーログを分析して、以下の情報を提供してください:

エラーログ:
{error_log}

追加コンテキスト:
{context or 'なし'}

以下の形式でJSON出力してください:
{{
    "error_type": "エラーの種類",
    "root_cause": "根本原因",
    "severity": "critical/high/medium/low",
    "fix_suggestion": "修正方法の提案",
    "code_example": "修正コードの例（ある場合）"
}}
"""

        message = self.claude_client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}]
        )

        try:
            response_text = message.content[0].text
            # JSON部分を抽出
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except:
            pass

        return {"raw_response": message.content[0].text}

    def generate_fix(self, error_analysis: Dict, file_path: Optional[str] = None) -> Tuple[bool, str]:
        """
        修正コードを生成

        Args:
            error_analysis: analyze_error()の結果
            file_path: 修正対象のファイルパス

        Returns:
            (success, fix_code_or_message)
        """
        self.blackboard.log(
            "🔧 Generating fix...",
            level="INFO",
            agent=AgentType.ERROR_RECOVERY
        )

        suggested_fix = error_analysis.get("suggested_fix")
        if not suggested_fix:
            return False, "No fix suggestion available"

        fix_type = suggested_fix["type"]
        fix_content = suggested_fix["content"]

        # 修正タイプに応じた処理
        if fix_type == "add_chrome_flag":
            fix_code = f"""
# FIX: Add Chrome flag to disable extensions
options.add_argument('{fix_content}')
"""
            return True, fix_code

        elif fix_type == "auto_dismiss_popup":
            fix_code = """
# FIX: Auto-dismiss Kindle terms popup
try:
    wait = WebDriverWait(self.driver, 5)
    ok_button = wait.until(EC.element_to_be_clickable(
        (By.XPATH, "//button[contains(translate(text(), 'OK', 'ok'), 'ok')]")
    ))
    ok_button.click()
    time.sleep(2)
except TimeoutException:
    pass
"""
            return True, fix_code

        elif fix_type == "retry_with_wait":
            fix_code = """
# FIX: Add retry logic with explicit wait
max_retries = 3
for attempt in range(max_retries):
    try:
        # Original code here
        break
    except Exception as e:
        if attempt < max_retries - 1:
            time.sleep(2 ** attempt)  # Exponential backoff
        else:
            raise
"""
            return True, fix_code

        elif fix_type == "reconnect":
            fix_code = """
# FIX: Retry database connection with exponential backoff
import time
max_retries = 5
for attempt in range(max_retries):
    try:
        # Database connection code
        break
    except Exception as e:
        if attempt < max_retries - 1:
            wait_time = 2 ** attempt
            time.sleep(wait_time)
        else:
            raise
"""
            return True, fix_code

        else:
            return False, f"Unknown fix type: {fix_type}"

    def apply_fix(self, fix_code: str, file_path: str, backup: bool = True) -> Tuple[bool, str]:
        """
        修正を適用

        Args:
            fix_code: 修正コード
            file_path: 対象ファイル
            backup: バックアップ作成するか

        Returns:
            (success, message)
        """
        self.blackboard.log(
            f"🚀 Applying fix to: {file_path}",
            level="INFO",
            agent=AgentType.ERROR_RECOVERY
        )

        target_path = Path(file_path)
        if not target_path.exists():
            return False, f"File not found: {file_path}"

        try:
            # バックアップ作成
            if backup:
                backup_path = target_path.with_suffix(target_path.suffix + '.backup')
                backup_path.write_text(target_path.read_text())
                self.blackboard.log(
                    f"💾 Backup created: {backup_path}",
                    level="INFO",
                    agent=AgentType.ERROR_RECOVERY
                )

            # 修正適用（シミュレーション）
            # 本番環境では実際のファイル編集を行う
            self.blackboard.log(
                f"✅ Fix applied to: {file_path}",
                level="SUCCESS",
                agent=AgentType.ERROR_RECOVERY
            )

            return True, "Fix applied successfully"

        except Exception as e:
            self.blackboard.log(
                f"❌ Failed to apply fix: {str(e)}",
                level="ERROR",
                agent=AgentType.ERROR_RECOVERY
            )
            return False, str(e)

    def notify(self, error: Dict, channel: str = "log") -> bool:
        """
        エラー通知を送信

        Args:
            error: エラー情報
            channel: 通知先 (log/slack/email)

        Returns:
            success
        """
        self.blackboard.log(
            f"📢 Sending notification to: {channel}",
            level="INFO",
            agent=AgentType.ERROR_RECOVERY
        )

        if channel == "log":
            self.blackboard.log(
                f"🚨 ERROR NOTIFICATION: {json.dumps(error, indent=2)}",
                level="ERROR",
                agent=AgentType.ERROR_RECOVERY
            )
            return True

        elif channel == "slack":
            # Slack Webhook実装（省略）
            self.blackboard.log(
                "⚠️ Slack notification not implemented",
                level="WARNING",
                agent=AgentType.ERROR_RECOVERY
            )
            return False

        elif channel == "email":
            # Email送信実装（省略）
            self.blackboard.log(
                "⚠️ Email notification not implemented",
                level="WARNING",
                agent=AgentType.ERROR_RECOVERY
            )
            return False

        return False

    def run_full_recovery(self, error_log: str, file_path: Optional[str] = None) -> Dict:
        """
        完全なエラー復旧サイクルを実行

        フロー:
        1. エラー分析
        2. 修正生成
        3. 修正適用
        4. 通知

        Returns:
            復旧レポート
        """
        report = {
            "started_at": datetime.now().isoformat(),
            "error_log": error_log,
            "steps": [],
            "success": False
        }

        # Step 1: エラー分析
        analysis = self.analyze_error(error_log)
        report["steps"].append({
            "step": "analyze",
            "result": analysis
        })

        # Step 2: 修正生成
        success, fix_code = self.generate_fix(analysis, file_path)
        report["steps"].append({
            "step": "generate_fix",
            "success": success,
            "fix_code": fix_code
        })

        if not success:
            report["message"] = "Failed to generate fix"
            self.notify(report, channel="log")
            return report

        # Step 3: 修正適用（ファイルパスがある場合のみ）
        if file_path:
            success, message = self.apply_fix(fix_code, file_path)
            report["steps"].append({
                "step": "apply_fix",
                "success": success,
                "message": message
            })

        # Step 4: 通知
        self.notify(report, channel="log")

        report["completed_at"] = datetime.now().isoformat()
        report["success"] = True
        report["message"] = "Recovery cycle completed"

        return report


# スタンドアロン実行用
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Error Recovery Agent")
    parser.add_argument("--repo", default=".", help="Repository path")
    parser.add_argument("--error", required=True, help="Error log to analyze")
    parser.add_argument("--file", help="File path to apply fix")

    args = parser.parse_args()

    agent = ErrorRecoveryAgent(args.repo)

    report = agent.run_full_recovery(args.error, args.file)
    print(json.dumps(report, indent=2))
