#!/usr/bin/env python3
"""
Kindle文字起こしツール セットアップウィザード

初心者でも簡単に環境設定できる対話型スクリプト
"""
import os
import sys
import subprocess
from pathlib import Path
from typing import Optional
import secrets
import string


class Colors:
    """コンソール出力用カラーコード"""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


def print_header(text: str):
    """ヘッダー出力"""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'=' * 60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text:^60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'=' * 60}{Colors.ENDC}\n")


def print_success(text: str):
    """成功メッセージ"""
    print(f"{Colors.OKGREEN}✅ {text}{Colors.ENDC}")


def print_warning(text: str):
    """警告メッセージ"""
    print(f"{Colors.WARNING}⚠️  {text}{Colors.ENDC}")


def print_error(text: str):
    """エラーメッセージ"""
    print(f"{Colors.FAIL}❌ {text}{Colors.ENDC}")


def print_info(text: str):
    """情報メッセージ"""
    print(f"{Colors.OKBLUE}ℹ️  {text}{Colors.ENDC}")


def ask_input(prompt: str, default: Optional[str] = None, required: bool = True) -> str:
    """ユーザー入力を取得"""
    if default:
        prompt_text = f"{prompt} (デフォルト: {default}): "
    else:
        prompt_text = f"{prompt}: "

    while True:
        value = input(prompt_text).strip()

        if value:
            return value
        elif default:
            return default
        elif not required:
            return ""
        else:
            print_warning("入力が必要です。もう一度入力してください。")


def ask_yes_no(prompt: str, default: bool = True) -> bool:
    """Yes/No質問"""
    default_text = "Y/n" if default else "y/N"
    response = input(f"{prompt} ({default_text}): ").strip().lower()

    if not response:
        return default
    return response in ['y', 'yes', 'はい']


def generate_secret_key(length: int = 50) -> str:
    """ランダムなシークレットキー生成"""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def check_command(command: str) -> bool:
    """コマンドが利用可能かチェック"""
    try:
        subprocess.run(
            [command, "--version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False
        )
        return True
    except FileNotFoundError:
        return False


def check_dependencies():
    """依存関係チェック"""
    print_header("依存関係チェック")

    dependencies = {
        "Python": ("python3", True),
        "Docker": ("docker", False),
        "Docker Compose": ("docker-compose", False),
        "Git": ("git", True),
    }

    all_ok = True
    for name, (command, required) in dependencies.items():
        if check_command(command):
            print_success(f"{name} が利用可能です")
        else:
            if required:
                print_error(f"{name} がインストールされていません（必須）")
                all_ok = False
            else:
                print_warning(f"{name} がインストールされていません（オプション）")

    return all_ok


def create_env_file():
    """環境変数ファイル作成"""
    print_header("環境変数ファイル作成")

    env_path = Path(".env")
    if env_path.exists():
        if not ask_yes_no("既に.envファイルが存在します。上書きしますか？", default=False):
            print_info(".envファイルの作成をスキップしました")
            return

    print_info("必要な情報を入力してください（Enter で デフォルト値を使用）")

    # データベース設定
    print("\n📊 データベース設定:")
    db_user = ask_input("PostgreSQL ユーザー名", default="kindle_user")
    db_password = ask_input("PostgreSQL パスワード", default=generate_secret_key(20))
    db_name = ask_input("データベース名", default="kindle_ocr")
    db_host = ask_input("データベースホスト", default="localhost")
    db_port = ask_input("データベースポート", default="5432")

    # API設定
    print("\n🔑 API設定:")
    anthropic_key = ask_input("Anthropic API Key (Claude)", required=False)
    openai_key = ask_input("OpenAI API Key (ChatGPT)", required=False)

    # S3設定
    print("\n☁️  S3ストレージ設定 (オプション):")
    use_s3 = ask_yes_no("S3ストレージを使用しますか？", default=False)

    s3_endpoint = ""
    s3_access_key = ""
    s3_secret_key = ""
    s3_bucket = ""

    if use_s3:
        s3_endpoint = ask_input("S3エンドポイント (例: s3.wasabisys.com)", required=False)
        s3_access_key = ask_input("S3 Access Key", required=False)
        s3_secret_key = ask_input("S3 Secret Key", required=False)
        s3_bucket = ask_input("S3 Bucket名", required=False)

    # セキュリティ設定
    print("\n🔒 セキュリティ設定:")
    jwt_secret = generate_secret_key(50)
    print_info(f"JWT Secret Key を自動生成しました: {jwt_secret[:10]}...")

    # .env ファイル書き込み
    env_content = f"""# Kindle文字起こしツール 環境変数設定
# 生成日: {subprocess.check_output(['date']).decode().strip()}

# ==================== データベース設定 ====================
DATABASE_URL=postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}
DB_USER={db_user}
DB_PASSWORD={db_password}
DB_NAME={db_name}
DB_HOST={db_host}
DB_PORT={db_port}

# ==================== Redis設定 ====================
REDIS_URL=redis://localhost:6379/0

# ==================== LLM API設定 ====================
ANTHROPIC_API_KEY={anthropic_key}
OPENAI_API_KEY={openai_key}

# ==================== S3ストレージ設定 ====================
S3_ENDPOINT={s3_endpoint}
S3_ACCESS_KEY={s3_access_key}
S3_SECRET_KEY={s3_secret_key}
S3_BUCKET={s3_bucket}

# ==================== セキュリティ設定 ====================
JWT_SECRET={jwt_secret}
API_KEY={generate_secret_key(32)}

# ==================== アプリケーション設定 ====================
APP_ENV=development
LOG_LEVEL=INFO
TESSDATA_PREFIX=/usr/share/tesseract-ocr/4.00/tessdata

# ==================== Streamlit設定 ====================
STREAMLIT_SERVER_HEADLESS=true
STREAMLIT_SERVER_PORT=8501

# ==================== FastAPI設定 ====================
API_HOST=0.0.0.0
API_PORT=8000
"""

    with open(env_path, "w", encoding="utf-8") as f:
        f.write(env_content)

    print_success(f".envファイルを作成しました: {env_path}")
    print_warning("⚠️  .envファイルには機密情報が含まれます。Gitにコミットしないでください！")


def install_dependencies():
    """Python依存関係インストール"""
    print_header("Python依存関係インストール")

    if not Path("requirements.txt").exists():
        print_error("requirements.txtが見つかりません")
        return False

    if ask_yes_no("Python依存関係をインストールしますか？", default=True):
        print_info("pip install -r requirements.txt を実行しています...")
        try:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
                check=True
            )
            print_success("依存関係のインストールが完了しました")
            return True
        except subprocess.CalledProcessError as e:
            print_error(f"インストール失敗: {e}")
            return False
    else:
        print_info("インストールをスキップしました")
        return True


def init_database():
    """データベース初期化"""
    print_header("データベース初期化")

    print_info("データベースを初期化します（Alembic マイグレーション）")

    if ask_yes_no("データベースマイグレーションを実行しますか？", default=True):
        try:
            # Alembic初回マイグレーション
            print_info("マイグレーションファイル生成中...")
            subprocess.run(
                ["alembic", "revision", "--autogenerate", "-m", "Initial migration"],
                check=True
            )

            print_info("マイグレーション適用中...")
            subprocess.run(["alembic", "upgrade", "head"], check=True)

            print_success("データベースマイグレーション完了")
            return True
        except subprocess.CalledProcessError as e:
            print_error(f"マイグレーション失敗: {e}")
            print_warning("データベース接続情報を確認してください")
            return False
    else:
        print_info("マイグレーションをスキップしました")
        return True


def create_directories():
    """必要なディレクトリ作成"""
    print_header("ディレクトリ作成")

    directories = [
        "captures",
        "uploads",
        "logs",
        "alembic/versions",
        "app/core",
        "app/models",
        "app/api",
        "app/services",
        "app/tasks",
        "app/ui"
    ]

    for directory in directories:
        dir_path = Path(directory)
        dir_path.mkdir(parents=True, exist_ok=True)
        print_success(f"{directory}/ を作成しました")


def setup_git():
    """Git設定"""
    print_header("Git設定")

    gitignore_path = Path(".gitignore")
    if not gitignore_path.exists():
        gitignore_content = """# Environment
.env
.env.local
*.env

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
env/
ENV/

# IDE
.vscode/
.idea/
*.swp

# Data
captures/
uploads/
logs/
*.db
*.sqlite

# OS
.DS_Store
Thumbs.db

# Docker
docker-compose.override.yml
"""
        with open(gitignore_path, "w", encoding="utf-8") as f:
            f.write(gitignore_content)
        print_success(".gitignoreを作成しました")


def print_next_steps():
    """次のステップ表示"""
    print_header("セットアップ完了！")

    print(f"{Colors.OKGREEN}🎉 セットアップが完了しました！{Colors.ENDC}\n")
    print(f"{Colors.BOLD}次のステップ:{Colors.ENDC}\n")
    print("1️⃣  ローカルで実行する場合:")
    print("   docker-compose up -d    # Docker環境起動")
    print("   または")
    print("   uvicorn app.main:app --reload  # FastAPI起動")
    print()
    print("2️⃣  Streamlit UI を起動:")
    print("   streamlit run app/ui/main.py")
    print()
    print("3️⃣  テストキャプチャ実行:")
    print("   python -m app.services.capture.pyautogui_capture")
    print()
    print(f"{Colors.WARNING}📖 詳細なドキュメントは README.md を参照してください{Colors.ENDC}")


def main():
    """メイン処理"""
    print_header("Kindle文字起こしツール セットアップウィザード")

    print(f"{Colors.OKCYAN}このウィザードでは以下の設定を行います:{Colors.ENDC}")
    print("  ✅ 依存関係チェック")
    print("  ✅ 環境変数ファイル作成")
    print("  ✅ Python依存関係インストール")
    print("  ✅ データベース初期化")
    print("  ✅ 必要なディレクトリ作成")
    print()

    if not ask_yes_no("セットアップを開始しますか？", default=True):
        print_info("セットアップをキャンセルしました")
        return

    # 各ステップ実行
    if not check_dependencies():
        print_error("必須の依存関係が不足しています")
        sys.exit(1)

    create_env_file()
    create_directories()
    setup_git()

    if install_dependencies():
        init_database()

    print_next_steps()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print_error("\nセットアップが中断されました")
        sys.exit(1)
    except Exception as e:
        print_error(f"予期しないエラー: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
