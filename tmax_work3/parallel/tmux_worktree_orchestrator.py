"""
T-Max Ultimate - tmux + worktree並列実行オーケストレーター

世界最高の並列処理システム:
- 最大42エージェント同時実行
- tmuxセッション管理
- git worktree分離実行
- 自動リソース割り当て
"""
import subprocess
import json
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
import threading
import time


class TmuxWorktreeOrchestrator:
    """
    tmux + worktree並列実行オーケストレーター

    機能:
    - tmuxセッション管理
    - worktree動的作成/削除
    - 並列タスク実行
    - リソース監視
    """

    def __init__(self, repository_path: str, session_name: str = "tmax-ultimate"):
        self.repo_path = Path(repository_path)
        self.session_name = session_name
        self.worktrees = {}
        self.tmux_windows = {}
        self.active_tasks = {}

        # ロック
        self.lock = threading.Lock()

        # tmuxセッションが存在するか確認
        self._ensure_tmux_session()

    def _ensure_tmux_session(self):
        """tmuxセッションが存在することを確認"""
        result = subprocess.run(
            ["tmux", "has-session", "-t", self.session_name],
            capture_output=True
        )

        if result.returncode != 0:
            # セッション作成
            subprocess.run(
                ["tmux", "new-session", "-d", "-s", self.session_name],
                check=True
            )
            print(f"✅ Created tmux session: {self.session_name}")
        else:
            print(f"✅ tmux session exists: {self.session_name}")

    def create_worktree(self, agent_id: str, branch_name: Optional[str] = None) -> Path:
        """
        エージェント用worktreeを作成

        Args:
            agent_id: エージェントID（例: "agent-01"）
            branch_name: ブランチ名（省略時は agent_id から生成）

        Returns:
            worktreeのパス
        """
        if branch_name is None:
            branch_name = f"parallel/{agent_id}"

        worktree_path = self.repo_path.parent / f".worktrees/{agent_id}"

        # 既存のworktreeをクリーンアップ
        if worktree_path.exists():
            self.remove_worktree(agent_id)

        # worktree作成
        subprocess.run(
            ["git", "worktree", "add", "-b", branch_name, str(worktree_path), "HEAD"],
            cwd=self.repo_path,
            check=True,
            capture_output=True
        )

        with self.lock:
            self.worktrees[agent_id] = {
                "path": worktree_path,
                "branch": branch_name,
                "created_at": datetime.now().isoformat()
            }

        print(f"✅ Created worktree: {agent_id} → {worktree_path}")
        return worktree_path

    def remove_worktree(self, agent_id: str):
        """worktreeを削除"""
        if agent_id not in self.worktrees:
            return

        worktree_info = self.worktrees[agent_id]
        worktree_path = worktree_info["path"]

        # worktree削除
        subprocess.run(
            ["git", "worktree", "remove", str(worktree_path), "--force"],
            cwd=self.repo_path,
            capture_output=True
        )

        # ブランチ削除
        subprocess.run(
            ["git", "branch", "-D", worktree_info["branch"]],
            cwd=self.repo_path,
            capture_output=True
        )

        with self.lock:
            del self.worktrees[agent_id]

        print(f"🗑️ Removed worktree: {agent_id}")

    def create_tmux_window(self, agent_id: str, worktree_path: Path) -> str:
        """
        エージェント用tmux windowを作成

        Args:
            agent_id: エージェントID
            worktree_path: worktreeのパス

        Returns:
            window ID
        """
        window_name = f"{agent_id}"

        # tmux window作成
        subprocess.run(
            [
                "tmux", "new-window",
                "-t", self.session_name,
                "-n", window_name,
                "-c", str(worktree_path)
            ],
            check=True
        )

        # window IDを取得
        result = subprocess.run(
            ["tmux", "display-message", "-p", "-t", f"{self.session_name}:{window_name}", "#{window_id}"],
            capture_output=True,
            text=True
        )
        window_id = result.stdout.strip()

        with self.lock:
            self.tmux_windows[agent_id] = {
                "window_id": window_id,
                "window_name": window_name,
                "worktree_path": worktree_path
            }

        print(f"✅ Created tmux window: {agent_id} → {window_id}")
        return window_id

    def send_command(self, agent_id: str, command: str):
        """
        tmux windowにコマンドを送信

        Args:
            agent_id: エージェントID
            command: 実行するコマンド
        """
        if agent_id not in self.tmux_windows:
            raise ValueError(f"No tmux window for agent: {agent_id}")

        window_info = self.tmux_windows[agent_id]
        window_id = window_info["window_id"]

        # コマンド送信
        subprocess.run(
            ["tmux", "send-keys", "-t", window_id, command, "Enter"],
            check=True
        )

        print(f"📤 Sent command to {agent_id}: {command[:50]}...")

    def execute_parallel_tasks(self, tasks: List[Dict]) -> Dict:
        """
        タスクを並列実行

        Args:
            tasks: タスクリスト
                [
                    {
                        "agent_id": "agent-01",
                        "command": "pytest tests/",
                        "timeout": 300
                    },
                    ...
                ]

        Returns:
            実行結果
        """
        print(f"\n🚀 Starting parallel execution: {len(tasks)} tasks")

        # 各タスクにworktree + tmux windowを割り当て
        for task in tasks:
            agent_id = task["agent_id"]

            # worktree作成
            worktree_path = self.create_worktree(agent_id)

            # tmux window作成
            self.create_tmux_window(agent_id, worktree_path)

            # コマンド実行
            command = task["command"]
            self.send_command(agent_id, command)

            # タスク記録
            with self.lock:
                self.active_tasks[agent_id] = {
                    **task,
                    "started_at": datetime.now().isoformat(),
                    "status": "running"
                }

        # すべて完了を待つ
        print("\n⏳ Waiting for all tasks to complete...")
        results = self._wait_all_complete(tasks)

        return results

    def _wait_all_complete(self, tasks: List[Dict], check_interval: int = 5) -> Dict:
        """
        すべてのタスクの完了を待つ

        Args:
            tasks: タスクリスト
            check_interval: チェック間隔（秒）

        Returns:
            実行結果
        """
        results = {}
        completed = set()

        while len(completed) < len(tasks):
            for task in tasks:
                agent_id = task["agent_id"]

                if agent_id in completed:
                    continue

                # タスク完了チェック（簡易版: ファイル存在確認）
                worktree_path = self.worktrees[agent_id]["path"]
                result_file = worktree_path / ".task_result.json"

                if result_file.exists():
                    # 結果読み込み
                    result = json.loads(result_file.read_text())
                    results[agent_id] = result
                    completed.add(agent_id)

                    with self.lock:
                        self.active_tasks[agent_id]["status"] = "completed"
                        self.active_tasks[agent_id]["completed_at"] = datetime.now().isoformat()

                    print(f"✅ Task completed: {agent_id}")

            # 未完了がある場合は待機
            if len(completed) < len(tasks):
                time.sleep(check_interval)

        return results

    def cleanup_all(self):
        """すべてのworktreeとtmux windowをクリーンアップ"""
        print("\n🧹 Cleaning up all resources...")

        # worktree削除
        for agent_id in list(self.worktrees.keys()):
            self.remove_worktree(agent_id)

        # tmux window削除
        for agent_id, window_info in list(self.tmux_windows.items()):
            window_id = window_info["window_id"]
            subprocess.run(
                ["tmux", "kill-window", "-t", window_id],
                capture_output=True
            )

        self.tmux_windows.clear()
        self.active_tasks.clear()

        print("✅ Cleanup complete")

    def get_status(self) -> Dict:
        """現在の状態を取得"""
        with self.lock:
            return {
                "session": self.session_name,
                "worktrees": len(self.worktrees),
                "windows": len(self.tmux_windows),
                "active_tasks": len([t for t in self.active_tasks.values() if t["status"] == "running"]),
                "completed_tasks": len([t for t in self.active_tasks.values() if t["status"] == "completed"]),
                "tasks": dict(self.active_tasks)
            }

    def attach_session(self):
        """tmuxセッションにアタッチ（手動監視用）"""
        print(f"\n📺 Attaching to tmux session: {self.session_name}")
        print(f"   Detach with: Ctrl-b d")
        subprocess.run(["tmux", "attach-session", "-t", self.session_name])


# Best-of-N並列実行ヘルパー
class BestOfNExecutor:
    """
    Best-of-N戦略実行

    同じタスクを複数エージェントに割り当て、
    Evaluatorで最良の結果を選出
    """

    def __init__(self, orchestrator: TmuxWorktreeOrchestrator, n: int = 3):
        self.orchestrator = orchestrator
        self.n = n

    def execute_best_of_n(self, task: Dict) -> Dict:
        """
        Best-of-N実行

        Args:
            task: 実行するタスク
                {
                    "command": "pytest tests/",
                    "timeout": 300
                }

        Returns:
            最良の結果
        """
        print(f"\n🏆 Best-of-N execution (N={self.n})")

        # N個のエージェントにタスクを割り当て
        parallel_tasks = []
        for i in range(self.n):
            agent_id = f"candidate-{i:02d}"
            parallel_tasks.append({
                "agent_id": agent_id,
                **task
            })

        # 並列実行
        results = self.orchestrator.execute_parallel_tasks(parallel_tasks)

        # Evaluatorで最良を選出（ここでは簡易版）
        winner = self._select_best(results)

        print(f"\n🥇 Winner: {winner['agent_id']}")
        return winner

    def _select_best(self, results: Dict) -> Dict:
        """
        最良の結果を選出（簡易版）

        実際のEvaluatorでは:
        - pytest結果
        - 差分の複雑度
        - コード品質
        - ドキュメント一貫性
        などを総合評価
        """
        # ここでは最初に成功したものを返す（簡易版）
        for agent_id, result in results.items():
            if result.get("success", False):
                return {
                    "agent_id": agent_id,
                    **result
                }

        # すべて失敗した場合は最初のものを返す
        agent_id = list(results.keys())[0]
        return {
            "agent_id": agent_id,
            **results[agent_id]
        }


# テスト＆デモ用コード
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="T-Max tmux + worktree Orchestrator")
    parser.add_argument("--demo", action="store_true", help="Run demo")
    parser.add_argument("--cleanup", action="store_true", help="Cleanup all resources")
    parser.add_argument("--status", action="store_true", help="Show status")
    parser.add_argument("--attach", action="store_true", help="Attach to tmux session")
    args = parser.parse_args()

    # Orchestrator初期化
    orchestrator = TmuxWorktreeOrchestrator(".")

    if args.cleanup:
        orchestrator.cleanup_all()

    elif args.status:
        status = orchestrator.get_status()
        print(json.dumps(status, indent=2))

    elif args.attach:
        orchestrator.attach_session()

    elif args.demo:
        print("🎬 Running demo...")

        # デモタスク
        tasks = [
            {
                "agent_id": "demo-agent-01",
                "command": "echo 'Agent 01 working...' && sleep 3 && echo '{\"success\": true}' > .task_result.json",
                "timeout": 10
            },
            {
                "agent_id": "demo-agent-02",
                "command": "echo 'Agent 02 working...' && sleep 5 && echo '{\"success\": true}' > .task_result.json",
                "timeout": 10
            },
            {
                "agent_id": "demo-agent-03",
                "command": "echo 'Agent 03 working...' && sleep 2 && echo '{\"success\": true}' > .task_result.json",
                "timeout": 10
            }
        ]

        # 並列実行
        results = orchestrator.execute_parallel_tasks(tasks)

        print("\n📊 Results:")
        print(json.dumps(results, indent=2))

        # クリーンアップ
        orchestrator.cleanup_all()

        print("\n✅ Demo complete!")

    else:
        print("Usage: python tmux_worktree_orchestrator.py [--demo|--cleanup|--status|--attach]")
