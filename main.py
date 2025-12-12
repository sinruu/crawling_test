#!/usr/bin/env python3
"""
우리금융 IR 크롤러 메인 실행 파일
"""
import argparse
import logging
import sys
from typing import Optional

from crawler.earnings import EarningsCrawler
from crawler.factbook import FactBookCrawler
from utils.downloader import PDFDownloader
from config import EARNINGS_DOWNLOAD_DIR, FACTBOOK_DOWNLOAD_DIR


def setup_logging(verbose: bool = False):
    """
    로깅 설정

    Args:
        verbose: 상세 로그 출력 여부
    """
    level = logging.DEBUG if verbose else logging.INFO
    format_str = '[%(levelname)s] %(message)s'

    logging.basicConfig(
        level=level,
        format=format_str,
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )


def crawl_earnings(download: bool = False) -> bool:
    """
    실적발표 크롤링 실행

    Args:
        download: PDF 다운로드 여부

    Returns:
        성공 여부
    """
    logger = logging.getLogger(__name__)
    logger.info("=" * 60)
    logger.info("실적발표 크롤링 시작")
    logger.info("=" * 60)

    # 크롤링
    crawler = EarningsCrawler()
    items = crawler.crawl()

    if not items:
        logger.warning("수집된 항목이 없습니다")
        return False

    # CSV 저장
    success = crawler.save_to_csv(items)
    if not success:
        return False

    # PDF 다운로드 (옵션)
    if download:
        logger.info("")
        logger.info("PDF 다운로드 시작")
        logger.info("-" * 60)

        downloader = PDFDownloader(EARNINGS_DOWNLOAD_DIR)
        download_items = [
            {'url': item['pdf_url'], 'filename': item['filename']}
            for item in items
        ]
        stats = downloader.download_multiple(download_items)

        logger.info("-" * 60)
        logger.info(
            f"다운로드 완료 - "
            f"성공: {stats['success']}, "
            f"실패: {stats['failed']}, "
            f"건너뜀: {stats['skipped']}"
        )

    logger.info("=" * 60)
    logger.info("실적발표 크롤링 완료")
    logger.info("=" * 60)

    return True


def crawl_factbook(download: bool = False) -> bool:
    """
    Fact Book 크롤링 실행

    Args:
        download: PDF 다운로드 여부

    Returns:
        성공 여부
    """
    logger = logging.getLogger(__name__)
    logger.info("=" * 60)
    logger.info("Fact Book 크롤링 시작")
    logger.info("=" * 60)

    # 크롤링
    crawler = FactBookCrawler()
    items = crawler.crawl()

    if not items:
        logger.warning("수집된 항목이 없습니다")
        return False

    # CSV 저장
    success = crawler.save_to_csv(items)
    if not success:
        return False

    # PDF 다운로드 (옵션)
    if download:
        logger.info("")
        logger.info("PDF 다운로드 시작")
        logger.info("-" * 60)

        downloader = PDFDownloader(FACTBOOK_DOWNLOAD_DIR)
        download_items = [
            {'url': item['pdf_url'], 'filename': item['filename']}
            for item in items
        ]
        stats = downloader.download_multiple(download_items)

        logger.info("-" * 60)
        logger.info(
            f"다운로드 완료 - "
            f"성공: {stats['success']}, "
            f"실패: {stats['failed']}, "
            f"건너뜀: {stats['skipped']}"
        )

    logger.info("=" * 60)
    logger.info("Fact Book 크롤링 완료")
    logger.info("=" * 60)

    return True


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(
        description='우리금융 IR 크롤러',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  python main.py                      # 메타데이터만 수집
  python main.py --download           # PDF까지 다운로드
  python main.py --type earnings      # 실적발표만
  python main.py --type factbook      # Fact Book만
  python main.py -d -v                # PDF 다운로드 + 상세 로그
        """
    )

    parser.add_argument(
        '--download', '-d',
        action='store_true',
        help='PDF 파일도 다운로드'
    )

    parser.add_argument(
        '--type', '-t',
        choices=['earnings', 'factbook', 'all'],
        default='all',
        help='크롤링할 대상 (기본값: all)'
    )

    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='상세 로그 출력'
    )

    args = parser.parse_args()

    # 로깅 설정
    setup_logging(args.verbose)

    logger = logging.getLogger(__name__)
    logger.info("우리금융 IR 크롤러 v1.0")
    logger.info("")

    # 크롤링 실행
    success_count = 0
    total_count = 0

    if args.type in ['earnings', 'all']:
        total_count += 1
        if crawl_earnings(args.download):
            success_count += 1
        logger.info("")

    if args.type in ['factbook', 'all']:
        total_count += 1
        if crawl_factbook(args.download):
            success_count += 1
        logger.info("")

    # 결과 출력
    if success_count == total_count:
        logger.info("✅ 모든 작업이 성공적으로 완료되었습니다")
        return 0
    elif success_count > 0:
        logger.warning(f"⚠️  일부 작업만 완료되었습니다 ({success_count}/{total_count})")
        return 1
    else:
        logger.error("❌ 모든 작업이 실패했습니다")
        return 1


if __name__ == "__main__":
    sys.exit(main())
