#!/usr/bin/env python3
"""
キャプチャ済み画像の重複検証スクリプト

キャプチャディレクトリ内の全画像のMD5ハッシュを計算し、
重複がないかチェックする。
"""

import hashlib
import logging
from pathlib import Path
import sys
from collections import defaultdict
from typing import Dict, List

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)


def calculate_file_hash(file_path: Path) -> str:
    """ファイルのMD5ハッシュを計算"""
    md5 = hashlib.md5()
    with open(file_path, 'rb') as f:
        while chunk := f.read(8192):
            md5.update(chunk)
    return md5.hexdigest()


def verify_capture_directory(capture_dir: Path) -> bool:
    """
    キャプチャディレクトリ内の画像を検証

    Args:
        capture_dir: キャプチャディレクトリパス

    Returns:
        bool: 重複がない場合True
    """
    if not capture_dir.exists():
        logger.error(f"❌ ディレクトリが見つかりません: {capture_dir}")
        return False

    # 全PNG画像を取得
    image_files = sorted(capture_dir.glob("page_*.png"))

    if not image_files:
        logger.warning(f"⚠️ 画像ファイルが見つかりません: {capture_dir}")
        return True

    logger.info(f"📂 検証ディレクトリ: {capture_dir}")
    logger.info(f"📊 画像ファイル数: {len(image_files)}")
    logger.info("=" * 60)

    # ハッシュ計算
    hash_to_files: Dict[str, List[Path]] = defaultdict(list)

    logger.info("🔍 ハッシュ計算中...")
    for i, image_file in enumerate(image_files, 1):
        file_hash = calculate_file_hash(image_file)
        hash_to_files[file_hash].append(image_file)

        if i % 10 == 0 or i == len(image_files):
            logger.info(f"   処理中: {i}/{len(image_files)} ファイル")

    # 重複チェック
    logger.info("=" * 60)
    logger.info("🔍 重複チェック結果:")
    logger.info("=" * 60)

    duplicates_found = False
    unique_hashes = len(hash_to_files)

    for file_hash, files in hash_to_files.items():
        if len(files) > 1:
            duplicates_found = True
            logger.error(f"❌ 重複検出: {len(files)}個のファイルが同一")
            logger.error(f"   ハッシュ: {file_hash}")
            for file in files:
                logger.error(f"   - {file.name}")

    logger.info("=" * 60)
    logger.info(f"📊 統計:")
    logger.info(f"   総ファイル数: {len(image_files)}")
    logger.info(f"   ユニークハッシュ数: {unique_hashes}")
    logger.info(f"   重複グループ数: {sum(1 for files in hash_to_files.values() if len(files) > 1)}")
    logger.info("=" * 60)

    if not duplicates_found:
        logger.info("✅ 重複なし: 全ての画像がユニークです")
        return True
    else:
        logger.error("❌ 重複あり: 同一画像が検出されました")
        logger.error("   ページめくりが正しく動作していない可能性があります")
        return False


def main():
    """メイン処理"""
    if len(sys.argv) < 2:
        logger.info("使用法: python3 verify_capture_duplicates.py <キャプチャディレクトリ>")
        logger.info("例: python3 verify_capture_duplicates.py captures/テスト本")

        # デフォルトでcapturesディレクトリ配下を検索
        captures_root = Path("captures")
        if captures_root.exists():
            subdirs = [d for d in captures_root.iterdir() if d.is_dir()]
            if subdirs:
                logger.info(f"\n利用可能なキャプチャディレクトリ:")
                for subdir in subdirs:
                    image_count = len(list(subdir.glob("page_*.png")))
                    logger.info(f"  - {subdir.name} ({image_count}ファイル)")

        sys.exit(1)

    capture_dir = Path(sys.argv[1])

    logger.info("\n" + "=" * 60)
    logger.info("キャプチャ画像重複検証")
    logger.info("=" * 60 + "\n")

    result = verify_capture_directory(capture_dir)

    sys.exit(0 if result else 1)


if __name__ == "__main__":
    main()
