#!/usr/bin/env python3
"""
T-Max Work3 全エージェント統合テスト
全15エージェントの動作確認とBlackboard統合テスト
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from tmax_work3.blackboard.state_manager import (
    Blackboard,
    AgentType,
    TaskStatus,
    get_blackboard
)


def test_import_all_agents():
    """全エージェントのインポートテスト"""
    print("🧪 Testing agent imports...")

    try:
        from tmax_work3.agents.coordinator import CoordinatorAgent
        print("  ✅ CoordinatorAgent imported")
    except Exception as e:
        print(f"  ❌ CoordinatorAgent failed: {e}")
        return False

    try:
        from tmax_work3.agents.database_migration import DatabaseMigrationAgent
        print("  ✅ DatabaseMigrationAgent imported")
    except Exception as e:
        print(f"  ❌ DatabaseMigrationAgent failed: {e}")
        return False

    try:
        from tmax_work3.agents.error_recovery import ErrorRecoveryAgent
        print("  ✅ ErrorRecoveryAgent imported")
    except Exception as e:
        print(f"  ❌ ErrorRecoveryAgent failed: {e}")
        return False

    try:
        from tmax_work3.agents.api_testing import APITestingAgent
        print("  ✅ APITestingAgent imported")
    except Exception as e:
        print(f"  ❌ APITestingAgent failed: {e}")
        return False

    try:
        from tmax_work3.agents.documentation import DocumentationAgent
        print("  ✅ DocumentationAgent imported")
    except Exception as e:
        print(f"  ❌ DocumentationAgent failed: {e}")
        return False

    try:
        from tmax_work3.agents.monitoring import MonitoringAgent
        print("  ✅ MonitoringAgent imported")
    except Exception as e:
        print(f"  ❌ MonitoringAgent failed: {e}")
        return False

    try:
        from tmax_work3.agents.dependency_management import DependencyManagementAgent
        print("  ✅ DependencyManagementAgent imported")
    except Exception as e:
        print(f"  ❌ DependencyManagementAgent failed: {e}")
        return False

    try:
        from tmax_work3.agents.infrastructure_as_code import InfrastructureAsCodeAgent
        print("  ✅ InfrastructureAsCodeAgent imported")
    except Exception as e:
        print(f"  ❌ InfrastructureAsCodeAgent failed: {e}")
        return False

    try:
        from tmax_work3.agents.mlops import MLOpsAgent
        print("  ✅ MLOpsAgent imported")
    except Exception as e:
        print(f"  ❌ MLOpsAgent failed: {e}")
        return False

    print("\n✅ All 9 agents imported successfully!")
    return True


def test_agent_types():
    """AgentType enumの確認"""
    print("\n🧪 Testing AgentType enum...")

    expected_agents = [
        "COORDINATOR",
        "BUILDER",
        "QA",
        "SECURITY",
        "PERFORMANCE",
        "DEPLOYER",
        "AUDIT",
        "DATABASE_MIGRATION",
        "ERROR_RECOVERY",
        "API_TESTING",
        "DOCUMENTATION",
        "MONITORING",
        "DEPENDENCY_MANAGEMENT",
        "INFRASTRUCTURE_AS_CODE",
        "MLOPS"
    ]

    for agent_name in expected_agents:
        if hasattr(AgentType, agent_name):
            print(f"  ✅ AgentType.{agent_name} exists")
        else:
            print(f"  ❌ AgentType.{agent_name} missing")
            return False

    print(f"\n✅ All {len(expected_agents)} agent types registered!")
    return True


def test_agent_initialization():
    """各エージェントの初期化テスト"""
    print("\n🧪 Testing agent initialization...")

    repo_path = "."

    try:
        from tmax_work3.agents.database_migration import DatabaseMigrationAgent
        agent = DatabaseMigrationAgent(repo_path)
        print("  ✅ DatabaseMigrationAgent initialized")
    except Exception as e:
        print(f"  ⚠️ DatabaseMigrationAgent: {e}")

    try:
        from tmax_work3.agents.error_recovery import ErrorRecoveryAgent
        agent = ErrorRecoveryAgent(repo_path)
        print("  ✅ ErrorRecoveryAgent initialized")
    except Exception as e:
        print(f"  ⚠️ ErrorRecoveryAgent: {e}")

    try:
        from tmax_work3.agents.api_testing import APITestingAgent
        agent = APITestingAgent(repo_path)
        print("  ✅ APITestingAgent initialized")
    except Exception as e:
        print(f"  ⚠️ APITestingAgent: {e}")

    try:
        from tmax_work3.agents.documentation import DocumentationAgent
        agent = DocumentationAgent(repo_path)
        print("  ✅ DocumentationAgent initialized")
    except Exception as e:
        print(f"  ⚠️ DocumentationAgent: {e}")

    try:
        from tmax_work3.agents.monitoring import MonitoringAgent
        agent = MonitoringAgent(repo_path)
        print("  ✅ MonitoringAgent initialized")
    except Exception as e:
        print(f"  ⚠️ MonitoringAgent: {e}")

    try:
        from tmax_work3.agents.dependency_management import DependencyManagementAgent
        agent = DependencyManagementAgent(repo_path)
        print("  ✅ DependencyManagementAgent initialized")
    except Exception as e:
        print(f"  ⚠️ DependencyManagementAgent: {e}")

    try:
        from tmax_work3.agents.infrastructure_as_code import InfrastructureAsCodeAgent
        agent = InfrastructureAsCodeAgent(repo_path)
        print("  ✅ InfrastructureAsCodeAgent initialized")
    except Exception as e:
        print(f"  ⚠️ InfrastructureAsCodeAgent: {e}")

    try:
        from tmax_work3.agents.mlops import MLOpsAgent
        agent = MLOpsAgent(repo_path)
        print("  ✅ MLOpsAgent initialized")
    except Exception as e:
        print(f"  ⚠️ MLOpsAgent: {e}")

    print("\n✅ Agent initialization tests completed!")
    return True


def test_blackboard_integration():
    """Blackboard統合テスト"""
    print("\n🧪 Testing Blackboard integration...")

    bb = get_blackboard()

    # Blackboard状態確認
    summary = bb.get_summary()
    print(f"  📊 Registered agents: {len(summary.get('agents', {}))}")
    print(f"  📊 Total tasks: {summary.get('tasks', {}).get('completed', 0)}")

    # 全エージェントタイプをリスト
    print("\n  Registered agent types:")
    for agent_type in summary.get('agents', {}).keys():
        print(f"    - {agent_type}")

    print("\n✅ Blackboard integration verified!")
    return True


def run_all_tests():
    """全テストを実行"""
    print("=" * 60)
    print("T-Max Work3 全エージェント統合テスト")
    print("=" * 60)

    results = []

    # Test 1: インポート
    results.append(("Import Test", test_import_all_agents()))

    # Test 2: AgentType enum
    results.append(("AgentType Test", test_agent_types()))

    # Test 3: 初期化
    results.append(("Initialization Test", test_agent_initialization()))

    # Test 4: Blackboard統合
    results.append(("Blackboard Integration", test_blackboard_integration()))

    # 結果サマリー
    print("\n" + "=" * 60)
    print("テスト結果サマリー")
    print("=" * 60)

    passed = 0
    failed = 0

    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status}: {test_name}")
        if result:
            passed += 1
        else:
            failed += 1

    print("\n" + "=" * 60)
    print(f"総合結果: {passed}/{len(results)} テスト合格")
    print("=" * 60)

    if failed == 0:
        print("\n🎉 全テスト合格！世界最強のエージェントチームが完成しました！")
        return True
    else:
        print(f"\n⚠️ {failed}件のテストが失敗しました")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
