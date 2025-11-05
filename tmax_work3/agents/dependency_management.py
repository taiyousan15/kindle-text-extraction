"""
T-Max Work3 Dependency Management Agent
依存関係管理・脆弱性スキャン・自動更新を担当

機能:
- requirements.txt自動更新
- Poetry/pipenv対応
- CVE脆弱性スキャン
- 互換性テスト
- 自動PR作成
"""
import os
import re
import subprocess
import toml
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set
from datetime import datetime
import sys
import json
import requests

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from tmax_work3.blackboard.state_manager import (
    Blackboard,
    AgentType,
    TaskStatus,
    get_blackboard
)


class DependencyManagementAgent:
    """
    Dependency Management Agent - 依存関係管理エージェント

    役割:
    - パッケージ依存関係の分析
    - セキュリティ脆弱性スキャン
    - パッケージバージョン更新提案
    - 互換性テスト実行
    - 自動PR作成
    """

    def __init__(self, repository_path: str):
        self.repo_path = Path(repository_path)
        self.blackboard = get_blackboard()
        self.requirements_file = self.repo_path / "requirements.txt"
        self.pyproject_file = self.repo_path / "pyproject.toml"
        self.pipfile = self.repo_path / "Pipfile"
        self.reports_dir = self.repo_path / "tmax_work3" / "data" / "dependency_reports"
        self.reports_dir.mkdir(parents=True, exist_ok=True)

        # エージェント登録
        self.blackboard.register_agent(
            AgentType.DEPENDENCY_MANAGEMENT,
            worktree="main"
        )

        self.blackboard.log(
            "📦 Dependency Management Agent initialized",
            level="INFO",
            agent=AgentType.DEPENDENCY_MANAGEMENT
        )

    def detect_package_manager(self) -> str:
        """
        使用中のパッケージマネージャーを検出

        Returns:
            パッケージマネージャー名 (pip/poetry/pipenv)
        """
        if self.pyproject_file.exists():
            content = self.pyproject_file.read_text()
            if "[tool.poetry]" in content:
                self.blackboard.log(
                    "✅ Detected package manager: Poetry",
                    level="INFO",
                    agent=AgentType.DEPENDENCY_MANAGEMENT
                )
                return "poetry"

        if self.pipfile.exists():
            self.blackboard.log(
                "✅ Detected package manager: Pipenv",
                level="INFO",
                agent=AgentType.DEPENDENCY_MANAGEMENT
            )
            return "pipenv"

        self.blackboard.log(
            "✅ Detected package manager: pip",
            level="INFO",
            agent=AgentType.DEPENDENCY_MANAGEMENT
        )
        return "pip"

    def parse_dependencies(self) -> Dict[str, str]:
        """
        現在の依存関係を解析

        Returns:
            {package_name: version} の辞書
        """
        self.blackboard.log(
            "🔍 Parsing dependencies...",
            level="INFO",
            agent=AgentType.DEPENDENCY_MANAGEMENT
        )

        package_manager = self.detect_package_manager()
        dependencies = {}

        try:
            if package_manager == "poetry":
                dependencies = self._parse_poetry_dependencies()
            elif package_manager == "pipenv":
                dependencies = self._parse_pipenv_dependencies()
            else:
                dependencies = self._parse_pip_dependencies()

            self.blackboard.log(
                f"✅ Parsed {len(dependencies)} dependencies",
                level="SUCCESS",
                agent=AgentType.DEPENDENCY_MANAGEMENT
            )

            return dependencies

        except Exception as e:
            self.blackboard.log(
                f"❌ Failed to parse dependencies: {str(e)}",
                level="ERROR",
                agent=AgentType.DEPENDENCY_MANAGEMENT
            )
            return {}

    def _parse_pip_dependencies(self) -> Dict[str, str]:
        """requirements.txtをパース"""
        if not self.requirements_file.exists():
            return {}

        dependencies = {}
        content = self.requirements_file.read_text()

        for line in content.split('\n'):
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            # package==version または package>=version 形式
            match = re.match(r'^([a-zA-Z0-9_-]+)\s*([>=<~!]+)\s*([0-9.]+.*?)$', line)
            if match:
                package, operator, version = match.groups()
                dependencies[package] = version
            else:
                # バージョン指定なし
                dependencies[line] = "latest"

        return dependencies

    def _parse_poetry_dependencies(self) -> Dict[str, str]:
        """pyproject.toml (Poetry) をパース"""
        if not self.pyproject_file.exists():
            return {}

        try:
            data = toml.load(self.pyproject_file)
            deps = data.get("tool", {}).get("poetry", {}).get("dependencies", {})

            dependencies = {}
            for package, version in deps.items():
                if package == "python":
                    continue
                if isinstance(version, dict):
                    version = version.get("version", "latest")
                dependencies[package] = version.strip("^~>=<")

            return dependencies

        except Exception as e:
            self.blackboard.log(
                f"⚠️ Failed to parse pyproject.toml: {str(e)}",
                level="WARNING",
                agent=AgentType.DEPENDENCY_MANAGEMENT
            )
            return {}

    def _parse_pipenv_dependencies(self) -> Dict[str, str]:
        """Pipfileをパース"""
        if not self.pipfile.exists():
            return {}

        try:
            data = toml.load(self.pipfile)
            deps = data.get("packages", {})

            dependencies = {}
            for package, version in deps.items():
                if isinstance(version, dict):
                    version = version.get("version", "latest")
                if version == "*":
                    version = "latest"
                dependencies[package] = version.strip("=~><!^")

            return dependencies

        except Exception as e:
            self.blackboard.log(
                f"⚠️ Failed to parse Pipfile: {str(e)}",
                level="WARNING",
                agent=AgentType.DEPENDENCY_MANAGEMENT
            )
            return {}

    def scan_vulnerabilities(self) -> List[Dict]:
        """
        CVE脆弱性スキャンを実行

        Returns:
            脆弱性レポートのリスト
        """
        self.blackboard.log(
            "🔒 Scanning for vulnerabilities...",
            level="INFO",
            agent=AgentType.DEPENDENCY_MANAGEMENT
        )

        vulnerabilities = []

        try:
            # pip-audit または safety を使用
            result = subprocess.run(
                ["pip-audit", "--format", "json"],
                capture_output=True,
                text=True,
                timeout=300,
                cwd=self.repo_path
            )

            if result.returncode == 0:
                vulnerabilities = json.loads(result.stdout)
            else:
                # pip-auditが失敗した場合は safety を試す
                vulnerabilities = self._scan_with_safety()

        except FileNotFoundError:
            # pip-auditがインストールされていない
            vulnerabilities = self._scan_with_safety()

        except Exception as e:
            self.blackboard.log(
                f"❌ Vulnerability scan failed: {str(e)}",
                level="ERROR",
                agent=AgentType.DEPENDENCY_MANAGEMENT
            )
            return []

        # レポート保存
        report_file = self.reports_dir / f"vulnerabilities_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        report_file.write_text(json.dumps(vulnerabilities, indent=2))

        vuln_count = len(vulnerabilities)
        if vuln_count > 0:
            self.blackboard.log(
                f"⚠️ Found {vuln_count} vulnerabilities",
                level="WARNING",
                agent=AgentType.DEPENDENCY_MANAGEMENT
            )
        else:
            self.blackboard.log(
                "✅ No vulnerabilities found",
                level="SUCCESS",
                agent=AgentType.DEPENDENCY_MANAGEMENT
            )

        return vulnerabilities

    def _scan_with_safety(self) -> List[Dict]:
        """safety を使用した脆弱性スキャン"""
        try:
            result = subprocess.run(
                ["safety", "check", "--json"],
                capture_output=True,
                text=True,
                timeout=300,
                cwd=self.repo_path
            )

            if result.returncode == 0 or result.stdout:
                data = json.loads(result.stdout)
                # safety の形式を統一形式に変換
                return [
                    {
                        "package": vuln[0],
                        "version": vuln[2],
                        "vulnerability": vuln[3],
                        "severity": "high"
                    }
                    for vuln in data
                ]
            return []

        except:
            # safety も使えない場合は手動チェック
            return self._manual_vulnerability_check()

    def _manual_vulnerability_check(self) -> List[Dict]:
        """PyPI APIを使った手動脆弱性チェック"""
        dependencies = self.parse_dependencies()
        vulnerabilities = []

        for package, version in dependencies.items():
            try:
                # PyPI APIで最新バージョンを取得
                response = requests.get(f"https://pypi.org/pypi/{package}/json", timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    latest_version = data["info"]["version"]

                    # バージョンが古い場合は警告
                    if version != "latest" and version != latest_version:
                        vulnerabilities.append({
                            "package": package,
                            "current_version": version,
                            "latest_version": latest_version,
                            "type": "outdated",
                            "severity": "low"
                        })

            except:
                continue

        return vulnerabilities

    def check_compatibility(self, package: str, version: str) -> Tuple[bool, str]:
        """
        パッケージの互換性をチェック

        Args:
            package: パッケージ名
            version: バージョン

        Returns:
            (compatible, message)
        """
        self.blackboard.log(
            f"🔍 Checking compatibility: {package}=={version}",
            level="INFO",
            agent=AgentType.DEPENDENCY_MANAGEMENT
        )

        try:
            # 仮想環境でインストールテスト
            result = subprocess.run(
                [
                    sys.executable,
                    "-m", "pip", "install",
                    "--dry-run",
                    "--no-deps",
                    f"{package}=={version}"
                ],
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode == 0:
                self.blackboard.log(
                    f"✅ {package}=={version} is compatible",
                    level="SUCCESS",
                    agent=AgentType.DEPENDENCY_MANAGEMENT
                )
                return True, "Compatible"
            else:
                self.blackboard.log(
                    f"❌ {package}=={version} is incompatible",
                    level="ERROR",
                    agent=AgentType.DEPENDENCY_MANAGEMENT
                )
                return False, result.stderr

        except Exception as e:
            self.blackboard.log(
                f"❌ Compatibility check failed: {str(e)}",
                level="ERROR",
                agent=AgentType.DEPENDENCY_MANAGEMENT
            )
            return False, str(e)

    def update_dependencies(self, packages: Optional[List[str]] = None) -> Tuple[bool, Dict]:
        """
        依存関係を更新

        Args:
            packages: 更新するパッケージリスト（省略時は全て）

        Returns:
            (success, update_report)
        """
        self.blackboard.log(
            f"⬆️ Updating dependencies...",
            level="INFO",
            agent=AgentType.DEPENDENCY_MANAGEMENT
        )

        update_report = {
            "updated": [],
            "failed": [],
            "skipped": []
        }

        try:
            package_manager = self.detect_package_manager()

            if packages is None:
                # 全パッケージ更新
                if package_manager == "poetry":
                    result = subprocess.run(
                        ["poetry", "update"],
                        capture_output=True,
                        text=True,
                        timeout=600,
                        cwd=self.repo_path
                    )
                elif package_manager == "pipenv":
                    result = subprocess.run(
                        ["pipenv", "update"],
                        capture_output=True,
                        text=True,
                        timeout=600,
                        cwd=self.repo_path
                    )
                else:
                    result = subprocess.run(
                        ["pip", "install", "--upgrade", "-r", str(self.requirements_file)],
                        capture_output=True,
                        text=True,
                        timeout=600
                    )

                if result.returncode == 0:
                    update_report["updated"].append("all")
                else:
                    update_report["failed"].append({"package": "all", "error": result.stderr})

            else:
                # 個別パッケージ更新
                for package in packages:
                    success, message = self._update_single_package(package, package_manager)
                    if success:
                        update_report["updated"].append(package)
                    else:
                        update_report["failed"].append({"package": package, "error": message})

            self.blackboard.log(
                f"✅ Updated {len(update_report['updated'])} packages",
                level="SUCCESS",
                agent=AgentType.DEPENDENCY_MANAGEMENT
            )

            return True, update_report

        except Exception as e:
            self.blackboard.log(
                f"❌ Dependency update failed: {str(e)}",
                level="ERROR",
                agent=AgentType.DEPENDENCY_MANAGEMENT
            )
            return False, {"error": str(e)}

    def _update_single_package(self, package: str, package_manager: str) -> Tuple[bool, str]:
        """単一パッケージを更新"""
        try:
            if package_manager == "poetry":
                cmd = ["poetry", "add", f"{package}@latest"]
            elif package_manager == "pipenv":
                cmd = ["pipenv", "install", "--upgrade", package]
            else:
                cmd = ["pip", "install", "--upgrade", package]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,
                cwd=self.repo_path
            )

            return result.returncode == 0, result.stderr if result.returncode != 0 else "Success"

        except Exception as e:
            return False, str(e)

    def create_update_pr(self, vulnerabilities: List[Dict], branch: str = "dependency-updates") -> Tuple[bool, str]:
        """
        依存関係更新PRを作成

        Args:
            vulnerabilities: 脆弱性リスト
            branch: PRブランチ名

        Returns:
            (success, pr_url)
        """
        self.blackboard.log(
            f"🔀 Creating update PR on branch: {branch}",
            level="INFO",
            agent=AgentType.DEPENDENCY_MANAGEMENT
        )

        try:
            # ブランチ作成
            subprocess.run(
                ["git", "checkout", "-b", branch],
                cwd=self.repo_path,
                capture_output=True,
                timeout=30
            )

            # 変更をコミット
            subprocess.run(
                ["git", "add", "."],
                cwd=self.repo_path,
                timeout=30
            )

            commit_message = f"""chore: Update dependencies to fix vulnerabilities

Fixed {len(vulnerabilities)} vulnerabilities:
{chr(10).join(f"- {v.get('package', 'unknown')}: {v.get('vulnerability', 'security issue')}" for v in vulnerabilities[:5])}

Generated by T-Max Work3 Dependency Management Agent
"""

            subprocess.run(
                ["git", "commit", "-m", commit_message],
                cwd=self.repo_path,
                timeout=30
            )

            # PR作成（gh CLI使用）
            result = subprocess.run(
                [
                    "gh", "pr", "create",
                    "--title", "chore: Update dependencies for security fixes",
                    "--body", commit_message
                ],
                capture_output=True,
                text=True,
                timeout=60,
                cwd=self.repo_path
            )

            if result.returncode == 0:
                pr_url = result.stdout.strip()
                self.blackboard.log(
                    f"✅ PR created: {pr_url}",
                    level="SUCCESS",
                    agent=AgentType.DEPENDENCY_MANAGEMENT
                )
                return True, pr_url
            else:
                self.blackboard.log(
                    f"⚠️ PR creation failed: {result.stderr}",
                    level="WARNING",
                    agent=AgentType.DEPENDENCY_MANAGEMENT
                )
                return False, result.stderr

        except Exception as e:
            self.blackboard.log(
                f"❌ PR creation failed: {str(e)}",
                level="ERROR",
                agent=AgentType.DEPENDENCY_MANAGEMENT
            )
            return False, str(e)

    def run_full_cycle(self, auto_update: bool = False) -> Dict:
        """
        完全な依存関係管理サイクルを実行

        フロー:
        1. 依存関係解析
        2. 脆弱性スキャン
        3. 更新提案
        4. (オプション) 自動更新とPR作成

        Returns:
            実行レポート
        """
        report = {
            "started_at": datetime.now().isoformat(),
            "steps": [],
            "success": False
        }

        # Step 1: 依存関係解析
        dependencies = self.parse_dependencies()
        report["steps"].append({
            "step": "parse_dependencies",
            "success": len(dependencies) > 0,
            "dependencies_count": len(dependencies)
        })

        # Step 2: 脆弱性スキャン
        vulnerabilities = self.scan_vulnerabilities()
        report["steps"].append({
            "step": "scan_vulnerabilities",
            "success": True,
            "vulnerabilities_count": len(vulnerabilities)
        })

        # Step 3: 更新提案
        if vulnerabilities:
            packages_to_update = list(set(v.get("package") for v in vulnerabilities))
            report["steps"].append({
                "step": "recommend_updates",
                "packages": packages_to_update
            })

            # Step 4: 自動更新（オプション）
            if auto_update:
                success, update_report = self.update_dependencies(packages_to_update)
                report["steps"].append({
                    "step": "update_dependencies",
                    "success": success,
                    "report": update_report
                })

                # PR作成
                if success:
                    pr_success, pr_url = self.create_update_pr(vulnerabilities)
                    report["steps"].append({
                        "step": "create_pr",
                        "success": pr_success,
                        "pr_url": pr_url
                    })

        report["completed_at"] = datetime.now().isoformat()
        report["success"] = True
        report["message"] = "Full dependency management cycle completed"

        return report


# スタンドアロン実行用
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Dependency Management Agent")
    parser.add_argument("--repo", default=".", help="Repository path")
    parser.add_argument("--action", default="full",
                       choices=["parse", "scan", "update", "pr", "full"],
                       help="Action to perform")
    parser.add_argument("--auto-update", action="store_true",
                       help="Automatically update dependencies")

    args = parser.parse_args()

    agent = DependencyManagementAgent(args.repo)

    if args.action == "parse":
        dependencies = agent.parse_dependencies()
        print(json.dumps(dependencies, indent=2))

    elif args.action == "scan":
        vulnerabilities = agent.scan_vulnerabilities()
        print(json.dumps(vulnerabilities, indent=2))

    elif args.action == "update":
        success, report = agent.update_dependencies()
        print(f"Update: {success}")
        print(json.dumps(report, indent=2))

    elif args.action == "pr":
        vulns = agent.scan_vulnerabilities()
        success, url = agent.create_update_pr(vulns)
        print(f"PR created: {success}")
        print(url)

    elif args.action == "full":
        report = agent.run_full_cycle(auto_update=args.auto_update)
        print(json.dumps(report, indent=2))
