"""
Auth Agent統合例
CoordinatorとAuth Agentの統合デモンストレーション
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from tmax_work3.agents.auth import AuthAgent
from tmax_work3.blackboard.state_manager import AgentType, get_blackboard


def main():
    """Auth Agent統合デモ"""
    print("=" * 60)
    print("Auth Agent Integration Demo")
    print("=" * 60)

    # Blackboard初期化
    blackboard = get_blackboard()

    # Auth Agent初期化
    auth_agent = AuthAgent(
        secret_key="demo-secret-key-12345",
        storage_dir="tmax_work3/security/demo"
    )

    print("\n[1] Register Agents")
    print("-" * 60)

    # 全エージェントをホワイトリストに登録
    agents_config = [
        (AgentType.COORDINATOR, ["admin", "coordinate", "assign"], 1000, 600),
        (AgentType.BUILDER, ["read", "write", "build"], 100, 60),
        (AgentType.QA, ["read", "test", "report"], 100, 60),
        (AgentType.SECURITY, ["read", "scan", "audit"], 50, 30),
        (AgentType.DEPLOYER, ["read", "deploy", "rollback"], 10, 10),
        (AgentType.PERFORMANCE, ["read", "monitor", "analyze"], 100, 60),
        (AgentType.AUDIT, ["read", "audit", "report"], 50, 30),
    ]

    for agent_type, permissions, max_tokens, rate_limit in agents_config:
        result = auth_agent.register_agent(
            agent_type=agent_type,
            permissions=permissions,
            max_tokens=max_tokens,
            rate_limit_per_minute=rate_limit
        )
        print(f"  {agent_type.value}: {'✓' if result else '✗'} (permissions: {permissions})")

    print("\n[2] Authenticate Agents and Issue Tokens")
    print("-" * 60)

    # トークン発行
    tokens = {}
    for agent_type, _, _, _ in agents_config:
        token = auth_agent.authenticate(
            agent_type=agent_type,
            metadata={
                "session": "demo-session",
                "timestamp": "2025-11-05"
            }
        )
        tokens[agent_type] = token
        if token:
            print(f"  {agent_type.value}: {token[:40]}...")
        else:
            print(f"  {agent_type.value}: Failed to authenticate")

    print("\n[3] Verify Tokens")
    print("-" * 60)

    for agent_type, token in tokens.items():
        if token:
            is_valid, payload = auth_agent.verify(token)
            if is_valid:
                print(f"  {agent_type.value}: ✓ Valid (jti: {payload['jti'][:16]}...)")
            else:
                print(f"  {agent_type.value}: ✗ Invalid")

    print("\n[4] Check Permissions")
    print("-" * 60)

    # BUILDER権限チェック
    builder_token = tokens.get(AgentType.BUILDER)
    if builder_token:
        permissions_to_check = ["build", "deploy", "admin"]
        for perm in permissions_to_check:
            has_perm = auth_agent.authorize(builder_token, perm)
            status = "✓" if has_perm else "✗"
            print(f"  BUILDER can '{perm}': {status}")

    print("\n[5] Revoke Token")
    print("-" * 60)

    # QAトークンを失効
    qa_token = tokens.get(AgentType.QA)
    if qa_token:
        print(f"  Revoking QA token...")
        result = auth_agent.revoke(qa_token)
        print(f"  Revocation: {'✓' if result else '✗'}")

        # 失効後の検証
        is_valid_after, _ = auth_agent.verify(qa_token)
        print(f"  QA token after revocation: {'✗ Invalid' if not is_valid_after else '✓ Valid'}")

    print("\n[6] Active Tokens")
    print("-" * 60)

    # アクティブトークン数を表示
    for agent_type, _, _, _ in agents_config:
        active_tokens = auth_agent.get_active_tokens(agent_type)
        print(f"  {agent_type.value}: {len(active_tokens)} active tokens")

    print("\n[7] Audit Logs")
    print("-" * 60)

    logs = auth_agent.get_audit_logs(limit=10)
    for i, log in enumerate(logs[-5:], 1):  # 最新5件
        print(f"  {i}. [{log['action']}] {log['agent_type']} - {log['status']}")

    print("\n[8] Update Permissions")
    print("-" * 60)

    # DEPLOYER権限を更新
    new_permissions = ["read", "deploy", "rollback", "emergency_stop"]
    result = auth_agent.update_agent_permissions(
        agent_type=AgentType.DEPLOYER,
        permissions=new_permissions
    )
    print(f"  DEPLOYER permissions updated: {'✓' if result else '✗'}")
    print(f"  New permissions: {new_permissions}")

    print("\n[9] Coordinator Integration")
    print("-" * 60)

    # Coordinatorがタスクを割り当てる際にトークンチェック
    coordinator_token = tokens.get(AgentType.COORDINATOR)
    if coordinator_token:
        # Coordinatorは管理者権限を持つ
        can_coordinate = auth_agent.authorize(coordinator_token, "coordinate")
        can_assign = auth_agent.authorize(coordinator_token, "assign")

        print(f"  Coordinator can 'coordinate': {'✓' if can_coordinate else '✗'}")
        print(f"  Coordinator can 'assign': {'✓' if can_assign else '✗'}")

        if can_coordinate and can_assign:
            print(f"  ✓ Coordinator is authorized to manage tasks")

    print("\n[10] Cleanup")
    print("-" * 60)

    cleaned = auth_agent.cleanup_expired_tokens()
    print(f"  Cleaned expired tokens: {cleaned}")

    print("\n" + "=" * 60)
    print("Demo Complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
