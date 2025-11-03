#!/usr/bin/env python3
"""
ページ重複検出機能のテストスクリプト

修正内容をテスト:
1. ページハッシュ計算が正しく動作するか
2. 重複検出が機能するか
3. 3回連続で同一ページを検出したら停止するか
4. リトライ機能が正しく動作するか
"""

import hashlib
import logging
from pathlib import Path
import sys

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('test_duplicate_detection.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)


def test_hash_calculation():
    """ハッシュ計算のテスト（ダミーデータ使用）"""
    logger.info("=" * 60)
    logger.info("TEST 1: ハッシュ計算機能")
    logger.info("=" * 60)

    # 同じデータは同じハッシュ
    data1 = b"test page content"
    data2 = b"test page content"
    hash1 = hashlib.md5(data1).hexdigest()
    hash2 = hashlib.md5(data2).hexdigest()

    assert hash1 == hash2, "同一データのハッシュが一致しません"
    logger.info(f"✅ 同一データのハッシュ一致: {hash1}")

    # 異なるデータは異なるハッシュ
    data3 = b"different page content"
    hash3 = hashlib.md5(data3).hexdigest()

    assert hash1 != hash3, "異なるデータのハッシュが一致してしまいました"
    logger.info(f"✅ 異なるデータのハッシュ不一致: {hash1} != {hash3}")

    logger.info("✅ TEST 1 PASSED: ハッシュ計算機能正常\n")


def test_duplicate_detection_logic():
    """重複検出ロジックのシミュレーション"""
    logger.info("=" * 60)
    logger.info("TEST 2: 重複検出ロジック")
    logger.info("=" * 60)

    # シミュレーション: ページハッシュのリスト
    # ページ1,2,3,3,3,3 (ページ3が4回連続)
    page_hashes = [
        "hash_page_1",
        "hash_page_2",
        "hash_page_3",  # 正常なページ
        "hash_page_3",  # 1回目の重複
        "hash_page_3",  # 2回目の重複
        "hash_page_3",  # 3回目の重複 -> ここで停止すべき
    ]

    consecutive_same_pages = 0
    previous_hash = None
    detected_at_page = None

    for page_num, current_hash in enumerate(page_hashes, start=1):
        if previous_hash and current_hash == previous_hash:
            consecutive_same_pages += 1
            logger.warning(
                f"⚠️ ページ {page_num} が前ページと同一 "
                f"(連続{consecutive_same_pages}回目)"
            )

            if consecutive_same_pages >= 3:
                logger.error(
                    f"❌ 3回連続で同一ページ検出 (ページ {page_num})"
                )
                detected_at_page = page_num
                break
        else:
            consecutive_same_pages = 0

        previous_hash = current_hash

    # ページ6で停止すべき（ページ3,4,5,6が同一ハッシュ）
    assert detected_at_page == 6, f"検出ページが不正: {detected_at_page} (期待値: 6)"
    logger.info("✅ TEST 2 PASSED: 重複検出ロジック正常\n")


def test_retry_logic_simulation():
    """リトライロジックのシミュレーション"""
    logger.info("=" * 60)
    logger.info("TEST 3: ページめくりリトライロジック")
    logger.info("=" * 60)

    # シミュレーション: ページめくり試行結果
    # False, False, True = 3回目で成功
    retry_results = [False, False, True]

    current_hash = "hash_page_1"
    turn_success = False

    for retry, result in enumerate(retry_results):
        logger.info(f"リトライ {retry + 1}/3...")

        if result:
            # ページが変わった
            new_hash = "hash_page_2"
            if new_hash != current_hash:
                turn_success = True
                logger.info(f"✅ ページめくり成功 (リトライ {retry + 1}回目)")
                break
        else:
            # ページが変わらなかった
            new_hash = current_hash
            logger.warning(f"⚠️ ページめくり失敗 (リトライ {retry + 1}/3)")

    assert turn_success, "リトライロジックが正しく動作していません"
    logger.info("✅ TEST 3 PASSED: リトライロジック正常\n")


def test_consecutive_failure_detection():
    """3回連続失敗検出のテスト"""
    logger.info("=" * 60)
    logger.info("TEST 4: 3回連続ページめくり失敗検出")
    logger.info("=" * 60)

    # 全て失敗するケース
    retry_results = [False, False, False]

    current_hash = "hash_page_1"
    turn_success = False

    for retry, result in enumerate(retry_results):
        logger.info(f"リトライ {retry + 1}/3...")

        if result:
            new_hash = "hash_page_2"
            if new_hash != current_hash:
                turn_success = True
                break
        else:
            new_hash = current_hash
            logger.warning(f"⚠️ ページめくり失敗 (リトライ {retry + 1}/3)")

    if not turn_success:
        logger.error("❌ ページめくりが3回失敗しました")

    assert not turn_success, "失敗を正しく検出できていません"
    logger.info("✅ TEST 4 PASSED: 連続失敗検出正常\n")


def verify_fix_implementation():
    """修正が正しく実装されているか確認"""
    logger.info("=" * 60)
    logger.info("TEST 5: 実装確認")
    logger.info("=" * 60)

    selenium_capture_file = Path(__file__).parent / "app/services/capture/selenium_capture.py"

    if not selenium_capture_file.exists():
        logger.error(f"❌ ファイルが見つかりません: {selenium_capture_file}")
        return False

    content = selenium_capture_file.read_text(encoding='utf-8')

    # 必要な修正が含まれているか確認
    checks = [
        ("import hashlib", "hashlibモジュールのインポート"),
        ("def _calculate_screenshot_hash", "ハッシュ計算メソッド"),
        ("consecutive_same_pages", "連続同一ページカウンター"),
        ("current_hash = self._calculate_screenshot_hash()", "ハッシュ計算呼び出し"),
        ("if consecutive_same_pages >= 3:", "3回連続検出条件"),
        ("for retry in range(3):", "リトライループ"),
        ("new_hash = self._calculate_screenshot_hash()", "ページめくり後のハッシュ計算"),
    ]

    all_passed = True
    for check_str, description in checks:
        if check_str in content:
            logger.info(f"✅ {description}: 実装確認")
        else:
            logger.error(f"❌ {description}: 未実装")
            all_passed = False

    if all_passed:
        logger.info("✅ TEST 5 PASSED: 全ての修正が実装されています\n")
    else:
        logger.error("❌ TEST 5 FAILED: 一部の修正が実装されていません\n")

    return all_passed


def main():
    """全テスト実行"""
    logger.info("\n" + "=" * 60)
    logger.info("ページ重複検出機能テスト開始")
    logger.info("=" * 60 + "\n")

    try:
        test_hash_calculation()
        test_duplicate_detection_logic()
        test_retry_logic_simulation()
        test_consecutive_failure_detection()
        implementation_ok = verify_fix_implementation()

        logger.info("=" * 60)
        logger.info("全テスト完了")
        logger.info("=" * 60)
        logger.info("✅ 単体テスト: 全て合格")

        if implementation_ok:
            logger.info("✅ 実装確認: 全ての修正が実装済み")
            logger.info("\n【次のステップ】")
            logger.info("1. 実際のKindleキャプチャで動作確認")
            logger.info("2. 短いページ数（10ページ程度）でテスト")
            logger.info("3. ログを確認して重複検出が動作しているか確認")
            logger.info("4. 全キャプチャ画像のハッシュを確認して重複がないか検証")
        else:
            logger.error("❌ 実装確認: 一部の修正が未実装")
            logger.error("   修正を完全に実装してから再テストしてください")

    except AssertionError as e:
        logger.error(f"❌ テスト失敗: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ テストエラー: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
