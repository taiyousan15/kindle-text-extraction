#!/usr/bin/env python3
"""
認証バイパススクリプト
個人使用モード（AUTH_ENABLED=false）対応のため、
全エンドポイントの認証依存関係を更新する
"""
import os
import re

def update_file(file_path):
    """ファイル内の認証依存関係を更新"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    original_content = content

    # Import文を更新
    content = content.replace(
        'from app.core.security import get_current_active_user',
        'from app.core.security import get_current_user_or_default'
    )

    # Depends使用箇所を更新
    content = content.replace(
        'Depends(get_current_active_user)',
        'Depends(get_current_user_or_default)'
    )

    # 変更があった場合のみファイルを更新
    if content != original_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✅ Updated: {file_path}")
        return True
    else:
        print(f"⏭️  Skipped: {file_path} (no changes needed)")
        return False

def main():
    """メイン処理"""
    print("🔄 Starting authentication bypass update...\n")

    # 更新対象のディレクトリ
    target_dirs = [
        'app/api/v1/endpoints/',
    ]

    updated_count = 0

    for target_dir in target_dirs:
        if not os.path.exists(target_dir):
            print(f"⚠️  Directory not found: {target_dir}")
            continue

        print(f"📁 Processing directory: {target_dir}")

        for filename in os.listdir(target_dir):
            if filename.endswith('.py') and filename != '__init__.py':
                file_path = os.path.join(target_dir, filename)
                if update_file(file_path):
                    updated_count += 1

    print(f"\n✨ Update complete! {updated_count} files updated.")
    print("\n🚀 Next steps:")
    print("   1. Restart the API server")
    print("   2. Verify Streamlit UI works without authentication")

if __name__ == '__main__':
    main()
