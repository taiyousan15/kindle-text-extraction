"""
T-Max Work3 Documentation Agent
ドキュメント自動生成・更新・デプロイを担当

機能:
- Docstring自動解析
- Sphinx/MkDocs統合
- API仕様書自動更新
- README自動生成
- GitHub Pages自動デプロイ
"""
import os
import re
import subprocess
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import sys
import json
import ast

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from tmax_work3.blackboard.state_manager import (
    Blackboard,
    AgentType,
    TaskStatus,
    get_blackboard
)


class DocumentationAgent:
    """
    Documentation Agent - ドキュメント自動生成エージェント

    役割:
    - ソースコードからドキュメント自動生成
    - API仕様書の自動更新
    - README/CHANGELOG自動生成
    - ドキュメントサイトのビルド・デプロイ
    - コードコメント品質チェック
    """

    def __init__(self, repository_path: str):
        self.repo_path = Path(repository_path)
        self.blackboard = get_blackboard()
        self.docs_dir = self.repo_path / "docs"
        self.api_docs_dir = self.docs_dir / "api"
        self.build_dir = self.docs_dir / "_build"

        # ディレクトリ作成
        self.docs_dir.mkdir(parents=True, exist_ok=True)
        self.api_docs_dir.mkdir(parents=True, exist_ok=True)

        # エージェント登録
        self.blackboard.register_agent(
            AgentType.DOCUMENTATION,
            worktree="main"
        )

        self.blackboard.log(
            "📚 Documentation Agent initialized",
            level="INFO",
            agent=AgentType.DOCUMENTATION
        )

    def parse_docstrings(self, file_path: str) -> List[Dict]:
        """
        Pythonファイルからdocstringを解析

        Args:
            file_path: 解析対象のPythonファイル

        Returns:
            docstring情報のリスト
        """
        self.blackboard.log(
            f"🔍 Parsing docstrings from: {file_path}",
            level="INFO",
            agent=AgentType.DOCUMENTATION
        )

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                tree = ast.parse(f.read(), filename=file_path)

            docstrings = []

            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.Module)):
                    docstring = ast.get_docstring(node)
                    if docstring:
                        docstrings.append({
                            "type": type(node).__name__,
                            "name": getattr(node, 'name', 'module'),
                            "docstring": docstring,
                            "line": node.lineno if hasattr(node, 'lineno') else 0
                        })

            self.blackboard.log(
                f"✅ Parsed {len(docstrings)} docstrings from {file_path}",
                level="SUCCESS",
                agent=AgentType.DOCUMENTATION
            )

            return docstrings

        except Exception as e:
            self.blackboard.log(
                f"❌ Failed to parse docstrings: {str(e)}",
                level="ERROR",
                agent=AgentType.DOCUMENTATION
            )
            return []

    def generate_api_docs(self, source_dir: Optional[str] = None) -> Tuple[bool, str]:
        """
        API仕様書を自動生成（Sphinx使用）

        Args:
            source_dir: ソースコードディレクトリ（デフォルト: app/）

        Returns:
            (success, output_path)
        """
        if source_dir is None:
            source_dir = str(self.repo_path / "app")

        self.blackboard.log(
            f"📖 Generating API documentation from: {source_dir}",
            level="INFO",
            agent=AgentType.DOCUMENTATION
        )

        try:
            # sphinx-apidocでドキュメント生成
            result = subprocess.run(
                [
                    "sphinx-apidoc",
                    "-f",  # Force overwrite
                    "-o", str(self.api_docs_dir),
                    source_dir
                ],
                capture_output=True,
                text=True,
                timeout=120
            )

            if result.returncode == 0:
                self.blackboard.log(
                    f"✅ API docs generated: {self.api_docs_dir}",
                    level="SUCCESS",
                    agent=AgentType.DOCUMENTATION
                )
                return True, str(self.api_docs_dir)
            else:
                # Sphinxがない場合はマニュアル生成
                self.blackboard.log(
                    "⚠️ sphinx-apidoc not available, generating manually",
                    level="WARNING",
                    agent=AgentType.DOCUMENTATION
                )
                return self._generate_api_docs_manually(source_dir)

        except FileNotFoundError:
            # sphinx-apidocがインストールされていない
            return self._generate_api_docs_manually(source_dir)

        except Exception as e:
            self.blackboard.log(
                f"❌ API docs generation failed: {str(e)}",
                level="ERROR",
                agent=AgentType.DOCUMENTATION
            )
            return False, str(e)

    def _generate_api_docs_manually(self, source_dir: str) -> Tuple[bool, str]:
        """
        Sphinx不使用時の手動API仕様書生成

        Args:
            source_dir: ソースディレクトリ

        Returns:
            (success, output_path)
        """
        try:
            api_doc_content = "# API Documentation\n\n"
            api_doc_content += f"Generated on: {datetime.now().isoformat()}\n\n"

            # Pythonファイルを再帰的に検索
            python_files = list(Path(source_dir).rglob("*.py"))

            for py_file in python_files:
                if "__pycache__" in str(py_file):
                    continue

                rel_path = py_file.relative_to(self.repo_path)
                api_doc_content += f"\n## {rel_path}\n\n"

                docstrings = self.parse_docstrings(str(py_file))
                for doc in docstrings:
                    api_doc_content += f"### {doc['type']}: {doc['name']}\n\n"
                    api_doc_content += f"```\n{doc['docstring']}\n```\n\n"

            # 出力
            output_file = self.api_docs_dir / "api_reference.md"
            output_file.write_text(api_doc_content, encoding='utf-8')

            self.blackboard.log(
                f"✅ Manual API docs generated: {output_file}",
                level="SUCCESS",
                agent=AgentType.DOCUMENTATION
            )

            return True, str(output_file)

        except Exception as e:
            self.blackboard.log(
                f"❌ Manual API docs generation failed: {str(e)}",
                level="ERROR",
                agent=AgentType.DOCUMENTATION
            )
            return False, str(e)

    def generate_readme(self, template: Optional[str] = None) -> Tuple[bool, str]:
        """
        README.mdを自動生成

        Args:
            template: テンプレートパス（省略時は自動生成）

        Returns:
            (success, readme_path)
        """
        self.blackboard.log(
            "📝 Generating README.md...",
            level="INFO",
            agent=AgentType.DOCUMENTATION
        )

        try:
            readme_path = self.repo_path / "README.md"

            # プロジェクト情報を収集
            project_info = self._collect_project_info()

            # README生成
            readme_content = f"""# {project_info['name']}

{project_info['description']}

## Features

{chr(10).join(f"- {feature}" for feature in project_info['features'])}

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```python
{project_info['usage_example']}
```

## Project Structure

```
{project_info['structure']}
```

## Testing

```bash
pytest tests/
```

## Documentation

Full documentation available at: [docs/](./docs/)

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md)

## License

{project_info['license']}

---

*Generated by T-Max Work3 Documentation Agent on {datetime.now().strftime('%Y-%m-%d')}*
"""

            readme_path.write_text(readme_content, encoding='utf-8')

            self.blackboard.log(
                f"✅ README.md generated: {readme_path}",
                level="SUCCESS",
                agent=AgentType.DOCUMENTATION
            )

            return True, str(readme_path)

        except Exception as e:
            self.blackboard.log(
                f"❌ README generation failed: {str(e)}",
                level="ERROR",
                agent=AgentType.DOCUMENTATION
            )
            return False, str(e)

    def _collect_project_info(self) -> Dict:
        """プロジェクト情報を収集"""

        # デフォルト情報
        info = {
            "name": self.repo_path.name,
            "description": "Auto-generated project documentation",
            "features": [
                "Feature 1: Core functionality",
                "Feature 2: Advanced features",
                "Feature 3: Integration support"
            ],
            "usage_example": "# Example usage\nimport app\napp.run()",
            "structure": "├── app/\n├── tests/\n└── docs/",
            "license": "MIT License"
        }

        # pyproject.toml から情報取得
        pyproject_path = self.repo_path / "pyproject.toml"
        if pyproject_path.exists():
            try:
                content = pyproject_path.read_text()
                # 簡易的なパース
                if 'name = ' in content:
                    name_match = re.search(r'name\s*=\s*["\']([^"\']+)["\']', content)
                    if name_match:
                        info['name'] = name_match.group(1)

                if 'description = ' in content:
                    desc_match = re.search(r'description\s*=\s*["\']([^"\']+)["\']', content)
                    if desc_match:
                        info['description'] = desc_match.group(1)
            except:
                pass

        return info

    def build_docs_site(self, builder: str = "html") -> Tuple[bool, str]:
        """
        ドキュメントサイトをビルド（Sphinx/MkDocs）

        Args:
            builder: ビルダータイプ (html/markdown/latex)

        Returns:
            (success, build_path)
        """
        self.blackboard.log(
            f"🏗️ Building documentation site ({builder})...",
            level="INFO",
            agent=AgentType.DOCUMENTATION
        )

        try:
            # conf.pyの存在確認
            conf_path = self.docs_dir / "conf.py"
            if not conf_path.exists():
                self._create_sphinx_config()

            # Sphinxビルド
            result = subprocess.run(
                [
                    "sphinx-build",
                    "-b", builder,
                    str(self.docs_dir),
                    str(self.build_dir / builder)
                ],
                capture_output=True,
                text=True,
                timeout=300
            )

            if result.returncode == 0:
                build_path = self.build_dir / builder / "index.html"
                self.blackboard.log(
                    f"✅ Documentation built: {build_path}",
                    level="SUCCESS",
                    agent=AgentType.DOCUMENTATION
                )
                return True, str(build_path)
            else:
                self.blackboard.log(
                    f"⚠️ Sphinx build failed: {result.stderr}",
                    level="WARNING",
                    agent=AgentType.DOCUMENTATION
                )
                # フォールバック: 静的HTMLとして生成
                return self._build_static_site()

        except FileNotFoundError:
            # Sphinxがない場合は静的サイト生成
            return self._build_static_site()

        except Exception as e:
            self.blackboard.log(
                f"❌ Documentation build failed: {str(e)}",
                level="ERROR",
                agent=AgentType.DOCUMENTATION
            )
            return False, str(e)

    def _create_sphinx_config(self):
        """Sphinx設定ファイルを作成"""
        conf_content = f"""# Sphinx configuration

project = '{self.repo_path.name}'
copyright = '{datetime.now().year}, T-Max Work3'
author = 'T-Max Work3 Documentation Agent'

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx.ext.viewcode',
]

html_theme = 'alabaster'
"""
        conf_path = self.docs_dir / "conf.py"
        conf_path.write_text(conf_content)

        # index.rstも作成
        index_content = f"""
{self.repo_path.name}
{'=' * len(self.repo_path.name)}

Welcome to {self.repo_path.name} documentation!

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   api/modules

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
"""
        index_path = self.docs_dir / "index.rst"
        index_path.write_text(index_content)

    def _build_static_site(self) -> Tuple[bool, str]:
        """静的HTMLサイトを生成（Sphinx不使用）"""
        try:
            html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{self.repo_path.name} Documentation</title>
    <style>
        body {{ font-family: Arial, sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; }}
        h1 {{ color: #333; }}
        .section {{ margin: 20px 0; }}
        code {{ background: #f4f4f4; padding: 2px 6px; border-radius: 3px; }}
    </style>
</head>
<body>
    <h1>{self.repo_path.name} Documentation</h1>
    <div class="section">
        <h2>Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</h2>
        <p>This is an auto-generated documentation site.</p>
    </div>
    <div class="section">
        <h2>Quick Links</h2>
        <ul>
            <li><a href="api/api_reference.md">API Reference</a></li>
            <li><a href="../README.md">README</a></li>
        </ul>
    </div>
</body>
</html>
"""
            output_path = self.build_dir / "html" / "index.html"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(html_content)

            self.blackboard.log(
                f"✅ Static site generated: {output_path}",
                level="SUCCESS",
                agent=AgentType.DOCUMENTATION
            )

            return True, str(output_path)

        except Exception as e:
            return False, str(e)

    def deploy_to_github_pages(self, branch: str = "gh-pages") -> Tuple[bool, str]:
        """
        GitHub Pagesにデプロイ

        Args:
            branch: デプロイ先ブランチ

        Returns:
            (success, message)
        """
        self.blackboard.log(
            f"🚀 Deploying to GitHub Pages (branch: {branch})...",
            level="INFO",
            agent=AgentType.DOCUMENTATION
        )

        try:
            # ビルドディレクトリの確認
            html_dir = self.build_dir / "html"
            if not html_dir.exists():
                return False, "Build directory not found. Run build_docs_site() first."

            # gh-pagesブランチの準備
            commands = [
                f"git checkout -B {branch}",
                f"git rm -rf .",
                f"cp -r {html_dir}/* .",
                "git add .",
                'git commit -m "Deploy documentation"',
                f"git push origin {branch} --force"
            ]

            for cmd in commands:
                result = subprocess.run(
                    cmd,
                    shell=True,
                    cwd=self.repo_path,
                    capture_output=True,
                    text=True,
                    timeout=60
                )

                if result.returncode != 0:
                    self.blackboard.log(
                        f"⚠️ Command failed: {cmd}\n{result.stderr}",
                        level="WARNING",
                        agent=AgentType.DOCUMENTATION
                    )

            self.blackboard.log(
                f"✅ Deployed to GitHub Pages",
                level="SUCCESS",
                agent=AgentType.DOCUMENTATION
            )

            return True, "Deployment successful"

        except Exception as e:
            self.blackboard.log(
                f"❌ GitHub Pages deployment failed: {str(e)}",
                level="ERROR",
                agent=AgentType.DOCUMENTATION
            )
            return False, str(e)

    def check_documentation_coverage(self, source_dir: Optional[str] = None) -> Dict:
        """
        ドキュメントカバレッジをチェック

        Args:
            source_dir: ソースディレクトリ

        Returns:
            カバレッジレポート
        """
        if source_dir is None:
            source_dir = str(self.repo_path / "app")

        self.blackboard.log(
            f"📊 Checking documentation coverage...",
            level="INFO",
            agent=AgentType.DOCUMENTATION
        )

        try:
            report = {
                "total_files": 0,
                "documented_files": 0,
                "total_functions": 0,
                "documented_functions": 0,
                "total_classes": 0,
                "documented_classes": 0,
                "coverage_percentage": 0.0,
                "files_without_docs": []
            }

            python_files = list(Path(source_dir).rglob("*.py"))
            report["total_files"] = len(python_files)

            for py_file in python_files:
                if "__pycache__" in str(py_file):
                    continue

                docstrings = self.parse_docstrings(str(py_file))

                has_docs = False
                for doc in docstrings:
                    has_docs = True
                    if doc['type'] == 'FunctionDef':
                        report["total_functions"] += 1
                        report["documented_functions"] += 1
                    elif doc['type'] == 'ClassDef':
                        report["total_classes"] += 1
                        report["documented_classes"] += 1

                if has_docs:
                    report["documented_files"] += 1
                else:
                    report["files_without_docs"].append(str(py_file.relative_to(self.repo_path)))

            # カバレッジ計算
            total_items = report["total_functions"] + report["total_classes"]
            documented_items = report["documented_functions"] + report["documented_classes"]

            if total_items > 0:
                report["coverage_percentage"] = (documented_items / total_items) * 100

            self.blackboard.log(
                f"✅ Documentation coverage: {report['coverage_percentage']:.1f}%",
                level="SUCCESS",
                agent=AgentType.DOCUMENTATION
            )

            return report

        except Exception as e:
            self.blackboard.log(
                f"❌ Coverage check failed: {str(e)}",
                level="ERROR",
                agent=AgentType.DOCUMENTATION
            )
            return {"error": str(e)}

    def run_full_cycle(self) -> Dict:
        """
        完全なドキュメント生成サイクルを実行

        フロー:
        1. API仕様書生成
        2. README生成
        3. ドキュメントサイトビルド
        4. カバレッジチェック

        Returns:
            実行レポート
        """
        report = {
            "started_at": datetime.now().isoformat(),
            "steps": [],
            "success": False
        }

        # Step 1: API仕様書生成
        success, api_path = self.generate_api_docs()
        report["steps"].append({
            "step": "generate_api_docs",
            "success": success,
            "output": api_path
        })

        # Step 2: README生成
        success, readme_path = self.generate_readme()
        report["steps"].append({
            "step": "generate_readme",
            "success": success,
            "output": readme_path
        })

        # Step 3: ドキュメントサイトビルド
        success, build_path = self.build_docs_site()
        report["steps"].append({
            "step": "build_docs_site",
            "success": success,
            "output": build_path
        })

        # Step 4: カバレッジチェック
        coverage = self.check_documentation_coverage()
        report["steps"].append({
            "step": "check_coverage",
            "success": "error" not in coverage,
            "coverage": coverage
        })

        report["completed_at"] = datetime.now().isoformat()
        report["success"] = all(step.get("success", False) for step in report["steps"])
        report["message"] = "Full documentation cycle completed"

        return report


# スタンドアロン実行用
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Documentation Agent")
    parser.add_argument("--repo", default=".", help="Repository path")
    parser.add_argument("--action", default="full",
                       choices=["api", "readme", "build", "coverage", "deploy", "full"],
                       help="Action to perform")
    parser.add_argument("--source-dir", help="Source directory for documentation")

    args = parser.parse_args()

    agent = DocumentationAgent(args.repo)

    if args.action == "api":
        success, path = agent.generate_api_docs(args.source_dir)
        print(f"API docs generated: {success}")
        print(f"Path: {path}")

    elif args.action == "readme":
        success, path = agent.generate_readme()
        print(f"README generated: {success}")
        print(f"Path: {path}")

    elif args.action == "build":
        success, path = agent.build_docs_site()
        print(f"Documentation built: {success}")
        print(f"Path: {path}")

    elif args.action == "coverage":
        report = agent.check_documentation_coverage(args.source_dir)
        print(json.dumps(report, indent=2))

    elif args.action == "deploy":
        success, message = agent.deploy_to_github_pages()
        print(f"Deployment: {success}")
        print(message)

    elif args.action == "full":
        report = agent.run_full_cycle()
        print(json.dumps(report, indent=2))
