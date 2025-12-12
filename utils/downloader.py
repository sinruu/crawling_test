"""
PDF 파일 다운로드 유틸리티
"""
import os
import time
import logging
import requests
from typing import Optional

from config import HEADERS, MAX_RETRIES, TIMEOUT, REQUEST_DELAY

# 로거 설정
logger = logging.getLogger(__name__)


class PDFDownloader:
    """PDF 파일 다운로드를 처리하는 클래스"""

    def __init__(self, download_dir: str):
        """
        Args:
            download_dir: PDF를 저장할 디렉토리 경로
        """
        self.download_dir = download_dir
        self._ensure_directory()

    def _ensure_directory(self):
        """다운로드 디렉토리가 존재하는지 확인하고 없으면 생성"""
        if not os.path.exists(self.download_dir):
            os.makedirs(self.download_dir)
            logger.info(f"디렉토리 생성: {self.download_dir}")

    def _file_exists(self, filename: str) -> bool:
        """
        파일이 이미 존재하는지 확인

        Args:
            filename: 확인할 파일명

        Returns:
            파일 존재 여부
        """
        filepath = os.path.join(self.download_dir, filename)
        return os.path.exists(filepath)

    def download(self, url: str, filename: str) -> bool:
        """
        PDF 파일을 다운로드

        Args:
            url: PDF 다운로드 URL
            filename: 저장할 파일명

        Returns:
            다운로드 성공 여부
        """
        # 파일 중복 체크
        if self._file_exists(filename):
            logger.info(f"[SKIP] {filename} 이미 존재")
            return True

        filepath = os.path.join(self.download_dir, filename)

        # 재시도 로직
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                # 서버 부하 방지를 위한 딜레이
                if attempt > 1:
                    time.sleep(REQUEST_DELAY * attempt)

                logger.debug(f"다운로드 시도 ({attempt}/{MAX_RETRIES}): {url}")

                response = requests.get(
                    url,
                    headers=HEADERS,
                    timeout=TIMEOUT,
                    stream=True
                )
                response.raise_for_status()

                # PDF 파일인지 확인
                content_type = response.headers.get('Content-Type', '')
                if 'pdf' not in content_type.lower():
                    logger.warning(f"PDF가 아닐 수 있음 (Content-Type: {content_type}): {url}")

                # 파일 저장
                with open(filepath, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)

                file_size = os.path.getsize(filepath)
                logger.info(f"[SUCCESS] {filename} 다운로드 완료 ({file_size:,} bytes)")

                # 다음 요청을 위한 딜레이
                time.sleep(REQUEST_DELAY)
                return True

            except requests.exceptions.Timeout:
                logger.warning(f"[RETRY {attempt}/{MAX_RETRIES}] {filename} 타임아웃")
                if attempt == MAX_RETRIES:
                    logger.error(f"[ERROR] {filename} 다운로드 실패: Timeout")

            except requests.exceptions.RequestException as e:
                logger.warning(f"[RETRY {attempt}/{MAX_RETRIES}] {filename} 요청 실패: {str(e)}")
                if attempt == MAX_RETRIES:
                    logger.error(f"[ERROR] {filename} 다운로드 실패: {str(e)}")

            except Exception as e:
                logger.error(f"[ERROR] {filename} 다운로드 중 예외 발생: {str(e)}")
                break

        # 실패 시 부분 다운로드 파일 삭제
        if os.path.exists(filepath):
            os.remove(filepath)
            logger.debug(f"불완전한 파일 삭제: {filepath}")

        return False

    def download_multiple(self, items: list) -> dict:
        """
        여러 PDF 파일을 다운로드

        Args:
            items: [{'url': str, 'filename': str}, ...] 형식의 리스트

        Returns:
            {'success': int, 'failed': int, 'skipped': int} 통계 정보
        """
        stats = {'success': 0, 'failed': 0, 'skipped': 0}

        logger.info(f"PDF 다운로드 시작 ({len(items)}개)")

        for item in items:
            url = item.get('url')
            filename = item.get('filename')

            if not url or not filename:
                logger.warning(f"잘못된 항목 건너뛰기: {item}")
                stats['failed'] += 1
                continue

            if self._file_exists(filename):
                stats['skipped'] += 1
                logger.info(f"[SKIP] {filename} 이미 존재")
                continue

            success = self.download(url, filename)
            if success:
                stats['success'] += 1
            else:
                stats['failed'] += 1

        logger.info(
            f"다운로드 완료 - "
            f"성공: {stats['success']}, "
            f"실패: {stats['failed']}, "
            f"건너뜀: {stats['skipped']}"
        )

        return stats
