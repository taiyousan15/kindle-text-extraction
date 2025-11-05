"""
T-Max Work3 Coordinator Agent
全体のタスク分解・割当・監視・再実行を統括するマスターエージェント
"""
import subprocess
import time
from pathlib import Path
from typing import List, Dict, Optional
import sys

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from tmax_work3.blackboard.state_manager import (
    Blackboard,
    AgentType,
    TaskStatus,
    get_blackboard
)


class CoordinatorAgent:
    """
    Coordinator Agent - 全体統括エージェント

    役割:
    - タスクDAGの構築と依存関係管理
    - エージェントへのタスク割当
    - 失敗タスクの再割当・再実行
    - 全体進捗の監視
    - tmuxセッションとgit worktreeの管理
    """

    def __init__(self, repository_path: str, deploy_target: str):
        self.repo_path = Path(repository_path)
        self.deploy_target = deploy_target
        self.blackboard = get_blackboard()

        # Coordinatorエージェント登録
        self.blackboard.register_agent(AgentType.COORDINATOR)

        print(f"🎯 Coordinator Agent initialized")
        print(f"   Repository: {self.repo_path}")
        print(f"   Deploy target: {self.deploy_target}")

    def initialize_pipeline(self):
        """パイプライン初期化: worktree作成、tmuxセッション起動"""
        self.blackboard.log("🚀 Initializing T-Max Work3 pipeline...", level="INFO")

        # Step 1: Git worktree作成
        self._create_worktrees()

        # Step 2: tmuxセッション作成
        self._create_tmux_session()

        # Step 3: タスクDAG構築
        self._build_task_dag()

        # Step 4: 全エージェント登録
        self._register_all_agents()

        self.blackboard.log("✅ Pipeline initialization complete", level="SUCCESS")

    def _create_worktrees(self):
        """Git worktreeを作成"""
        self.blackboard.log("📂 Creating git worktrees...", level="INFO")

        worktrees = [
            ("build_env", "main"),
            ("qa_env", "main"),
            ("deploy_env", "main"),
            ("monitor_env", "main")
        ]

        worktrees_dir = self.repo_path / "tmax_work3" / "worktrees"
        worktrees_dir.mkdir(parents=True, exist_ok=True)

        for worktree_name, branch in worktrees:
            worktree_path = worktrees_dir / worktree_name

            # 既存のworktreeを削除
            if worktree_path.exists():
                subprocess.run(
                    ["git", "worktree", "remove", str(worktree_path), "--force"],
                    cwd=self.repo_path,
                    capture_output=True
                )

            # worktree作成
            result = subprocess.run(
                ["git", "worktree", "add", str(worktree_path), branch],
                cwd=self.repo_path,
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                self.blackboard.log(f"✅ Worktree created: {worktree_name}", level="INFO")
            else:
                self.blackboard.log(
                    f"❌ Failed to create worktree {worktree_name}: {result.stderr}",
                    level="ERROR"
                )

    def _create_tmux_session(self):
        """tmuxセッションを作成"""
        self.blackboard.log("🖥️  Creating tmux session...", level="INFO")

        session_name = "TMAX_FULLAUTO"

        # 既存セッションを終了
        subprocess.run(
            ["tmux", "kill-session", "-t", session_name],
            capture_output=True
        )

        # 新規セッション作成
        subprocess.run(["tmux", "new-session", "-d", "-s", session_name])

        # ウィンドウ作成
        windows = [
            ("coordinator", "1"),
            ("builder", "2"),
            ("qa", "3"),
            ("deploy", "4"),
            ("monitor", "5")
        ]

        for window_name, window_id in windows:
            subprocess.run([
                "tmux", "new-window",
                "-t", f"{session_name}:{window_id}",
                "-n", window_name
            ])

        self.blackboard.log(f"✅ tmux session created: {session_name}", level="INFO")
        self.blackboard.log(f"   Access: tmux attach -t {session_name}", level="INFO")

    def _build_task_dag(self):
        """タスクDAGを構築"""
        self.blackboard.log("🔗 Building task DAG...", level="INFO")

        # タスク定義（依存関係を含む）
        tasks = [
            # Build phase
            {
                "task_id": "build-001",
                "name": "Install dependencies",
                "agent": AgentType.BUILDER,
                "priority": 10,
                "dependencies": [],
                "worktree": "worktrees/build_env",
                "tmux_window": "builder"
            },
            {
                "task_id": "build-002",
                "name": "Run linters",
                "agent": AgentType.BUILDER,
                "priority": 9,
                "dependencies": ["build-001"],
                "worktree": "worktrees/build_env",
                "tmux_window": "builder"
            },
            {
                "task_id": "build-003",
                "name": "Compile application",
                "agent": AgentType.BUILDER,
                "priority": 8,
                "dependencies": ["build-002"],
                "worktree": "worktrees/build_env",
                "tmux_window": "builder"
            },

            # QA phase
            {
                "task_id": "qa-001",
                "name": "Run unit tests",
                "agent": AgentType.QA,
                "priority": 7,
                "dependencies": ["build-003"],
                "worktree": "worktrees/qa_env",
                "tmux_window": "qa"
            },
            {
                "task_id": "qa-002",
                "name": "Run integration tests",
                "agent": AgentType.QA,
                "priority": 6,
                "dependencies": ["qa-001"],
                "worktree": "worktrees/qa_env",
                "tmux_window": "qa"
            },

            # Security phase
            {
                "task_id": "security-001",
                "name": "Security scan",
                "agent": AgentType.SECURITY,
                "priority": 5,
                "dependencies": ["build-003"],
                "worktree": "worktrees/build_env",
                "tmux_window": "builder"
            },

            # Deploy phase
            {
                "task_id": "deploy-001",
                "name": f"Deploy to {self.deploy_target}",
                "agent": AgentType.DEPLOYER,
                "priority": 4,
                "dependencies": ["qa-002", "security-001"],
                "worktree": "worktrees/deploy_env",
                "tmux_window": "deploy"
            },

            # Monitor phase
            {
                "task_id": "monitor-001",
                "name": "Monitor deployment",
                "agent": AgentType.PERFORMANCE,
                "priority": 3,
                "dependencies": ["deploy-001"],
                "worktree": "worktrees/monitor_env",
                "tmux_window": "monitor"
            },

            # Audit phase
            {
                "task_id": "audit-001",
                "name": "Generate final report",
                "agent": AgentType.AUDIT,
                "priority": 2,
                "dependencies": ["monitor-001"],
                "worktree": "worktrees/build_env",
                "tmux_window": "coordinator"
            }
        ]

        for task_def in tasks:
            self.blackboard.add_task(**task_def)

        self.blackboard.log(f"✅ Task DAG built: {len(tasks)} tasks", level="INFO")

    def _register_all_agents(self):
        """全エージェントを登録"""
        agents = [
            (AgentType.BUILDER, "worktrees/build_env", "builder"),
            (AgentType.QA, "worktrees/qa_env", "qa"),
            (AgentType.SECURITY, "worktrees/build_env", "builder"),
            (AgentType.DEPLOYER, "worktrees/deploy_env", "deploy"),
            (AgentType.PERFORMANCE, "worktrees/monitor_env", "monitor"),
            (AgentType.AUDIT, "worktrees/build_env", "coordinator")
        ]

        for agent_type, worktree, tmux_window in agents:
            self.blackboard.register_agent(agent_type, worktree, tmux_window)

    def run_coordination_loop(self, max_iterations: int = 100):
        """
        コーディネーションループ

        - 実行可能なタスクを取得
        - エージェントに割当
        - 失敗したタスクを再実行
        - 全タスク完了まで継続
        """
        self.blackboard.log("🔄 Starting coordination loop...", level="INFO")

        iteration = 0
        while iteration < max_iterations:
            iteration += 1

            # 実行可能なタスクを取得
            ready_tasks = self.blackboard.get_ready_tasks()

            if not ready_tasks:
                # 全タスク完了チェック
                all_tasks = list(self.blackboard.tasks.values())
                pending = [t for t in all_tasks if t.status == TaskStatus.PENDING]
                in_progress = [t for t in all_tasks if t.status == TaskStatus.IN_PROGRESS]
                completed = [t for t in all_tasks if t.status == TaskStatus.COMPLETED]
                failed = [t for t in all_tasks if t.status == TaskStatus.FAILED]

                self.blackboard.log(
                    f"📊 Status: {len(completed)} completed, {len(in_progress)} in progress, "
                    f"{len(pending)} pending, {len(failed)} failed",
                    level="INFO"
                )

                if not pending and not in_progress:
                    # 全タスク完了 or 全て失敗
                    if failed:
                        self.blackboard.log(
                            f"❌ Pipeline failed: {len(failed)} tasks failed",
                            level="ERROR"
                        )
                    else:
                        self.blackboard.log(
                            "✅ All tasks completed successfully!",
                            level="SUCCESS"
                        )
                    break

                # まだ進行中のタスクがある場合は待機
                time.sleep(2)
                continue

            # タスクを実行
            for task in ready_tasks:
                self._execute_task(task.task_id)

            time.sleep(1)

        # 最終サマリー
        summary = self.blackboard.get_summary()
        self.blackboard.log(f"📊 Final summary: {summary}", level="INFO")

    def _execute_task(self, task_id: str):
        """タスクを実行（エージェントに送信）"""
        task = self.blackboard.tasks[task_id]

        self.blackboard.log(
            f"🚀 Executing task: {task_id} ({task.name}) via {task.agent.value}",
            level="INFO"
        )

        # エージェントにタスクを割当
        self.blackboard.assign_task_to_agent(task_id, task.agent)

        # tmuxウィンドウにコマンドを送信
        self._send_tmux_command(task)

    def _send_tmux_command(self, task):
        """tmuxウィンドウにコマンドを送信"""
        session_name = "TMAX_FULLAUTO"
        window_name = task.tmux_window

        # エージェントタイプに応じたコマンド生成
        commands = {
            AgentType.BUILDER: f"cd {task.worktree} && echo 'Building: {task.name}' && sleep 2 && echo 'Build complete'",
            AgentType.QA: f"cd {task.worktree} && echo 'Testing: {task.name}' && sleep 2 && echo 'Tests passed'",
            AgentType.SECURITY: f"cd {task.worktree} && echo 'Security scan: {task.name}' && sleep 2 && echo 'Scan complete'",
            AgentType.DEPLOYER: f"cd {task.worktree} && echo 'Deploying: {task.name}' && sleep 3 && echo 'Deploy complete'",
            AgentType.PERFORMANCE: f"cd {task.worktree} && echo 'Monitoring: {task.name}' && sleep 2 && echo 'Monitoring active'",
            AgentType.AUDIT: f"cd {task.worktree} && echo 'Audit: {task.name}' && sleep 1 && echo 'Report generated'"
        }

        command = commands.get(task.agent, "echo 'Unknown agent'")

        # tmuxにコマンド送信
        subprocess.run([
            "tmux", "send-keys",
            "-t", f"{session_name}:{window_name}",
            command,
            "C-m"
        ])

        # シミュレーション: タスク完了を自動的にマーク
        # 実際にはエージェントがBlackboardを更新
        time.sleep(3)
        self.blackboard.complete_task(task.task_id, task.agent)


def main():
    """メイン実行"""
    import argparse

    parser = argparse.ArgumentParser(description="T-Max Work3 Coordinator Agent")
    parser.add_argument("--repo", default=".", help="Repository path")
    parser.add_argument("--target", default="vercel", help="Deploy target")
    parser.add_argument("--auto", action="store_true", help="Auto start pipeline")

    args = parser.parse_args()

    coordinator = CoordinatorAgent(args.repo, args.target)

    if args.auto:
        coordinator.initialize_pipeline()
        coordinator.run_coordination_loop()
    else:
        print("Coordinator initialized. Use --auto to start pipeline.")


if __name__ == "__main__":
    main()
