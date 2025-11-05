"""
T-Max Work3 Blackboard Architecture - Shared State Manager
全エージェントが状態を共有するための中央集権的なメッセージボード
"""
import json
import os
import threading
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any
from collections import defaultdict


class TaskStatus(Enum):
    """タスクステータス"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"
    RETRY = "retry"


class AgentType(Enum):
    """エージェントタイプ"""
    COORDINATOR = "coordinator"
    BUILDER = "builder"
    QA = "qa"
    SECURITY = "security"
    PERFORMANCE = "performance"
    DEPLOYER = "deployer"
    AUDIT = "audit"
    # 新規追加エージェント（2025-11-05）
    DATABASE_MIGRATION = "database_migration"
    ERROR_RECOVERY = "error_recovery"
    API_TESTING = "api_testing"
    DOCUMENTATION = "documentation"
    MONITORING = "monitoring"
    DEPENDENCY_MANAGEMENT = "dependency_management"
    INFRASTRUCTURE_AS_CODE = "infrastructure_as_code"
    MLOPS = "mlops"
    RAG = "rag"  # Hybrid Search RAG Agent


@dataclass
class Task:
    """タスクデータ構造"""
    task_id: str
    name: str
    agent: AgentType
    status: TaskStatus
    priority: int
    dependencies: List[str]
    worktree: Optional[str]
    tmux_window: Optional[str]
    created_at: str
    started_at: Optional[str]
    completed_at: Optional[str]
    error: Optional[str]
    retry_count: int
    metadata: Dict[str, Any]


@dataclass
class AgentState:
    """エージェント状態"""
    agent_type: AgentType
    status: str  # idle, working, error
    current_task: Optional[str]
    completed_tasks: List[str]
    failed_tasks: List[str]
    last_heartbeat: str
    worktree: Optional[str]
    tmux_window: Optional[str]


class Blackboard:
    """
    Blackboard Architecture実装

    全エージェントが読み書きできる共有メモリ空間。
    タスクDAG、エージェント状態、ログ、メトリクスを一元管理。
    """

    def __init__(self, storage_path: str = "tmax_work3/blackboard/state.json"):
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

        self.lock = threading.RLock()

        # 状態データ
        self.tasks: Dict[str, Task] = {}
        self.agents: Dict[AgentType, AgentState] = {}
        self.logs: List[Dict[str, Any]] = []
        self.metrics: Dict[str, Any] = defaultdict(dict)

        # DAGグラフ
        self.task_graph: Dict[str, List[str]] = {}  # task_id -> [dependent_task_ids]

        # ロード
        self._load_state()

        print(f"✅ Blackboard initialized: {self.storage_path}")

    def add_task(
        self,
        task_id: str,
        name: str,
        agent: AgentType,
        priority: int = 5,
        dependencies: Optional[List[str]] = None,
        worktree: Optional[str] = None,
        tmux_window: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Task:
        """タスクを追加"""
        with self.lock:
            task = Task(
                task_id=task_id,
                name=name,
                agent=agent,
                status=TaskStatus.PENDING,
                priority=priority,
                dependencies=dependencies or [],
                worktree=worktree,
                tmux_window=tmux_window,
                created_at=datetime.now().isoformat(),
                started_at=None,
                completed_at=None,
                error=None,
                retry_count=0,
                metadata=metadata or {}
            )

            self.tasks[task_id] = task
            self._save_state()

            self.log(f"📝 Task added: {task_id} ({name}) -> {agent.value}", level="INFO")
            return task

    def update_task_status(
        self,
        task_id: str,
        status: TaskStatus,
        error: Optional[str] = None
    ):
        """タスクステータスを更新"""
        with self.lock:
            if task_id not in self.tasks:
                raise ValueError(f"Task {task_id} not found")

            task = self.tasks[task_id]
            old_status = task.status
            task.status = status

            if status == TaskStatus.IN_PROGRESS and task.started_at is None:
                task.started_at = datetime.now().isoformat()

            if status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
                task.completed_at = datetime.now().isoformat()

            if error:
                task.error = error

            self._save_state()

            self.log(
                f"🔄 Task status updated: {task_id} ({old_status.value} -> {status.value})",
                level="INFO" if status != TaskStatus.FAILED else "ERROR"
            )

    def get_ready_tasks(self) -> List[Task]:
        """実行可能なタスクを取得（依存関係が解決済み）"""
        with self.lock:
            ready = []

            for task in self.tasks.values():
                if task.status != TaskStatus.PENDING:
                    continue

                # 依存関係チェック
                dependencies_met = all(
                    self.tasks.get(dep_id, Task(
                        task_id=dep_id, name="", agent=AgentType.COORDINATOR,
                        status=TaskStatus.FAILED, priority=0, dependencies=[],
                        worktree=None, tmux_window=None, created_at="",
                        started_at=None, completed_at=None, error=None,
                        retry_count=0, metadata={}
                    )).status == TaskStatus.COMPLETED
                    for dep_id in task.dependencies
                )

                if dependencies_met:
                    ready.append(task)

            # 優先度でソート
            return sorted(ready, key=lambda t: t.priority, reverse=True)

    def register_agent(
        self,
        agent_type: AgentType,
        worktree: Optional[str] = None,
        tmux_window: Optional[str] = None
    ):
        """エージェントを登録"""
        with self.lock:
            self.agents[agent_type] = AgentState(
                agent_type=agent_type,
                status="idle",
                current_task=None,
                completed_tasks=[],
                failed_tasks=[],
                last_heartbeat=datetime.now().isoformat(),
                worktree=worktree,
                tmux_window=tmux_window
            )

            self._save_state()
            self.log(f"🤖 Agent registered: {agent_type.value}", level="INFO")

    def update_agent_heartbeat(self, agent_type: AgentType):
        """エージェントのハートビートを更新"""
        with self.lock:
            if agent_type in self.agents:
                self.agents[agent_type].last_heartbeat = datetime.now().isoformat()

    def assign_task_to_agent(self, task_id: str, agent_type: AgentType):
        """タスクをエージェントに割り当て"""
        with self.lock:
            if agent_type not in self.agents:
                raise ValueError(f"Agent {agent_type} not registered")

            agent = self.agents[agent_type]
            agent.status = "working"
            agent.current_task = task_id

            self.update_task_status(task_id, TaskStatus.IN_PROGRESS)
            self._save_state()

            self.log(f"📌 Task assigned: {task_id} -> {agent_type.value}", level="INFO")

    def complete_task(self, task_id: str, agent_type: AgentType):
        """タスク完了"""
        with self.lock:
            self.update_task_status(task_id, TaskStatus.COMPLETED)

            if agent_type in self.agents:
                agent = self.agents[agent_type]
                agent.status = "idle"
                agent.current_task = None
                agent.completed_tasks.append(task_id)

            self._save_state()

    def fail_task(self, task_id: str, agent_type: AgentType, error: str):
        """タスク失敗"""
        with self.lock:
            task = self.tasks[task_id]
            task.retry_count += 1

            # リトライ判定
            if task.retry_count < 3:
                self.update_task_status(task_id, TaskStatus.RETRY, error=error)
                self.log(f"🔄 Task retry: {task_id} (attempt {task.retry_count}/3)", level="WARNING")
            else:
                self.update_task_status(task_id, TaskStatus.FAILED, error=error)
                self.log(f"❌ Task failed: {task_id} - {error}", level="ERROR")

            if agent_type in self.agents:
                agent = self.agents[agent_type]
                agent.status = "idle"
                agent.current_task = None
                agent.failed_tasks.append(task_id)

            self._save_state()

    def log(self, message: str, level: str = "INFO", agent: Optional[AgentType] = None):
        """ログを記録"""
        with self.lock:
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "level": level,
                "agent": agent.value if agent else None,
                "message": message
            }

            self.logs.append(log_entry)

            # コンソールにも出力
            icon = {"INFO": "ℹ️", "WARNING": "⚠️", "ERROR": "❌", "SUCCESS": "✅"}.get(level, "📝")
            print(f"{icon} [{level}] {message}")

            # ログが大きくなりすぎないよう制限
            if len(self.logs) > 1000:
                self.logs = self.logs[-1000:]

    def set_metric(self, category: str, key: str, value: Any):
        """メトリクスを設定"""
        with self.lock:
            self.metrics[category][key] = value
            self._save_state()

    def get_metrics(self) -> Dict[str, Any]:
        """全メトリクスを取得"""
        with self.lock:
            return dict(self.metrics)

    def get_summary(self) -> Dict[str, Any]:
        """現在の状態サマリーを取得"""
        with self.lock:
            task_stats = defaultdict(int)
            for task in self.tasks.values():
                task_stats[task.status.value] += 1

            agent_stats = {}
            for agent_type, agent_state in self.agents.items():
                agent_stats[agent_type.value] = {
                    "status": agent_state.status,
                    "completed": len(agent_state.completed_tasks),
                    "failed": len(agent_state.failed_tasks)
                }

            return {
                "timestamp": datetime.now().isoformat(),
                "tasks": dict(task_stats),
                "agents": agent_stats,
                "metrics": dict(self.metrics)
            }

    def _save_state(self):
        """状態をファイルに保存"""
        state = {
            "tasks": {
                task_id: {
                    **asdict(task),
                    "agent": task.agent.value,
                    "status": task.status.value
                }
                for task_id, task in self.tasks.items()
            },
            "agents": {
                agent.value: {
                    "agent_type": agent_state.agent_type.value,
                    "status": agent_state.status,
                    "current_task": agent_state.current_task,
                    "completed_tasks": agent_state.completed_tasks,
                    "failed_tasks": agent_state.failed_tasks,
                    "last_heartbeat": agent_state.last_heartbeat,
                    "worktree": agent_state.worktree,
                    "tmux_window": agent_state.tmux_window
                }
                for agent, agent_state in self.agents.items()
            },
            "logs": self.logs[-100:],  # 最新100件のみ保存
            "metrics": dict(self.metrics)
        }

        with open(self.storage_path, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=2, ensure_ascii=False)

    def _load_state(self):
        """状態をファイルからロード"""
        if not self.storage_path.exists():
            return

        try:
            with open(self.storage_path, 'r', encoding='utf-8') as f:
                state = json.load(f)

            # タスクを復元
            for task_id, task_data in state.get("tasks", {}).items():
                task_data["agent"] = AgentType(task_data["agent"])
                task_data["status"] = TaskStatus(task_data["status"])
                self.tasks[task_id] = Task(**task_data)

            # エージェントを復元
            for agent_str, agent_data in state.get("agents", {}).items():
                agent_data["agent_type"] = AgentType(agent_data["agent_type"])
                self.agents[AgentType(agent_str)] = AgentState(**agent_data)

            self.logs = state.get("logs", [])
            self.metrics = defaultdict(dict, state.get("metrics", {}))

            print(f"✅ Blackboard state loaded from {self.storage_path}")

        except Exception as e:
            print(f"⚠️ Failed to load blackboard state: {e}")


# グローバルBlackboardインスタンス
_blackboard: Optional[Blackboard] = None


def get_blackboard() -> Blackboard:
    """グローバルBlackboardインスタンスを取得"""
    global _blackboard
    if _blackboard is None:
        _blackboard = Blackboard()
    return _blackboard


if __name__ == "__main__":
    # テスト
    bb = Blackboard("tmax_work3/blackboard/test_state.json")

    # タスク追加
    bb.add_task(
        "build-001",
        "Install dependencies",
        AgentType.BUILDER,
        priority=10,
        worktree="worktrees/build_env"
    )

    bb.add_task(
        "build-002",
        "Run tests",
        AgentType.QA,
        priority=8,
        dependencies=["build-001"],
        worktree="worktrees/qa_env"
    )

    # エージェント登録
    bb.register_agent(AgentType.BUILDER, worktree="worktrees/build_env")
    bb.register_agent(AgentType.QA, worktree="worktrees/qa_env")

    # タスク実行シミュレーション
    ready_tasks = bb.get_ready_tasks()
    print(f"\n📋 Ready tasks: {[t.task_id for t in ready_tasks]}")

    if ready_tasks:
        task = ready_tasks[0]
        bb.assign_task_to_agent(task.task_id, task.agent)
        time.sleep(1)
        bb.complete_task(task.task_id, task.agent)

    # サマリー表示
    summary = bb.get_summary()
    print(f"\n📊 Summary:")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
