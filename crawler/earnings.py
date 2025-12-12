"""
실적발표 크롤러 (selenium-stealth 기반)
"""
import os
import re
import time
import logging
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime
from typing import List, Dict, Optional
from urllib.parse import urljoin

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium_stealth import stealth
from webdriver_manager.chrome import ChromeDriverManager

from config import (
    EARNINGS_URL, EARNINGS_CSV, BASE_URL, DATA_DIR,
    REQUEST_DELAY, MAX_RETRIES, CSV_COLUMNS,
    HEADLESS, PAGE_LOAD_TIMEOUT, IMPLICIT_WAIT
)

logger = logging.getLogger(__name__)


class EarningsCrawler:
    """실적발표 크롤러 클래스 (Selenium 기반)"""

    def __init__(self):
        self.url = EARNINGS_URL
        self.driver = None

    def _setup_driver(self):
        """
        Selenium Chrome WebDriver 설정 및 생성 (stealth 적용)
        """
        try:
            options = Options()

            # 헤드리스 모드 설정
            if HEADLESS:
                options.add_argument('--headless=new')

            # 추가 옵션
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('--window-size=1920,1080')

            # SSL 인증서 오류 무시
            options.add_argument('--ignore-certificate-errors')
            options.add_argument('--allow-insecure-localhost')

            # 자동화 감지 방지
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)

            # ChromeDriver 생성 (webdriver-manager로 자동 설치)
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)

            # Stealth 설정 적용
            stealth(self.driver,
                    languages=["ko-KR", "ko", "en-US", "en"],
                    vendor="Google Inc.",
                    platform="Win32",
                    webgl_vendor="Intel Inc.",
                    renderer="Intel Iris OpenGL Engine",
                    fix_hairline=True,
                    )

            # 타임아웃 설정
            self.driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)
            self.driver.implicitly_wait(IMPLICIT_WAIT)

            logger.info("Selenium Chrome WebDriver 초기화 완료 (stealth 적용)")

        except Exception as e:
            logger.error(f"WebDriver 초기화 실패: {str(e)}")
            raise

    def _parse_quarter(self, title: str) -> Optional[str]:
        """
        제목에서 분기 정보를 추출하여 파일명 형식으로 변환

        Args:
            title: 게시글 제목

        Returns:
            파일명 (예: "2025_3Q_실적발표.pdf") 또는 None
        """
        # 패턴: 2025년 3분기, 2025년 1Q, 2025 3Q 등
        patterns = [
            r'(\d{4})\s*년?\s*(\d)[분]*기',  # 2025년 3분기
            r'(\d{4})\s*[-._]?\s*(\d)Q',    # 2025-3Q, 2025_3Q
            r'(\d{4})\s*(\d)Q',              # 2025 3Q
            r'(\d{4})\s*Q(\d)',              # 2025 Q3
        ]

        for pattern in patterns:
            match = re.search(pattern, title, re.IGNORECASE)
            if match:
                year, quarter = match.groups()
                return f"{year}_{quarter}Q_실적발표.pdf"

        # 분기 정보를 찾을 수 없는 경우 제목 기반으로 생성
        logger.warning(f"분기 정보 추출 실패, 제목 기반 파일명 생성: {title}")
        safe_title = re.sub(r'[^\w\s-]', '', title).strip()
        safe_title = re.sub(r'[-\s]+', '_', safe_title)
        return f"{safe_title[:50]}.pdf"

    def _parse_date(self, date_str: str) -> str:
        """
        날짜 문자열을 표준 형식(YYYY.MM.DD)으로 변환

        Args:
            date_str: 원본 날짜 문자열

        Returns:
            YYYY.MM.DD 형식의 날짜 문자열
        """
        # 이미 YYYY.MM.DD 형식인 경우
        if re.match(r'\d{4}\.\d{2}\.\d{2}', date_str):
            return date_str

        # 다양한 날짜 형식 처리
        date_formats = [
            '%Y-%m-%d',
            '%Y/%m/%d',
            '%Y.%m.%d',
            '%Y년 %m월 %d일',
        ]

        for fmt in date_formats:
            try:
                dt = datetime.strptime(date_str.strip(), fmt)
                return dt.strftime('%Y.%m.%d')
            except ValueError:
                continue

        logger.warning(f"날짜 형식 변환 실패: {date_str}")
        return date_str

    def _fetch_page(self, url: str, visit_home_first: bool = True) -> Optional[BeautifulSoup]:
        """
        Selenium을 사용하여 웹페이지를 가져와서 BeautifulSoup 객체로 반환

        Args:
            url: 크롤링할 URL
            visit_home_first: 메인 페이지를 먼저 방문할지 여부

        Returns:
            BeautifulSoup 객체 또는 None
        """
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                logger.debug(f"페이지 요청 시도 ({attempt}/{MAX_RETRIES}): {url}")

                # 재시도 시 딜레이
                if attempt > 1:
                    time.sleep(REQUEST_DELAY * attempt)

                # 첫 시도 시 메인 페이지 먼저 방문 (세션 생성)
                if attempt == 1 and visit_home_first:
                    logger.info("메인 페이지 먼저 방문 중...")
                    self.driver.get(BASE_URL)
                    time.sleep(2)  # 메인 페이지 로딩 대기

                # 페이지 로드
                self.driver.get(url)

                # 페이지 로딩 대기 (body 태그가 로드될 때까지)
                WebDriverWait(self.driver, PAGE_LOAD_TIMEOUT).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )

                # 추가 로딩 시간 (동적 콘텐츠를 위해)
                time.sleep(REQUEST_DELAY * 3)

                # 페이지 소스 가져오기
                page_source = self.driver.page_source
                return BeautifulSoup(page_source, 'lxml')

            except TimeoutException:
                logger.warning(f"페이지 로드 타임아웃 ({attempt}/{MAX_RETRIES}): {url}")
                if attempt == MAX_RETRIES:
                    logger.error(f"페이지 요청 최종 실패: {url}")
                    return None

            except WebDriverException as e:
                logger.warning(f"WebDriver 오류 ({attempt}/{MAX_RETRIES}): {str(e)}")
                if attempt == MAX_RETRIES:
                    logger.error(f"페이지 요청 최종 실패: {url}")
                    return None

            except Exception as e:
                logger.error(f"예상치 못한 오류: {str(e)}")
                return None

        return None

    def _parse_items(self, soup: BeautifulSoup) -> List[Dict]:
        """
        페이지에서 게시글 정보를 파싱 (DIV 리스트 구조)

        Args:
            soup: BeautifulSoup 객체

        Returns:
            게시글 정보 리스트
        """
        items = []

        # DIV 리스트 구조 찾기
        list_containers = soup.find_all('div', class_='list-tyle1')
        logger.debug(f"발견된 리스트 컨테이너 개수: {len(list_containers)}")

        for container_idx, container in enumerate(list_containers):
            logger.debug(f"컨테이너 {container_idx + 1} 파싱 시도")

            # 각 list 아이템 찾기
            list_items = container.find_all('div', class_='list')
            logger.debug(f"리스트 항목 개수: {len(list_items)}")

            for item_idx, item in enumerate(list_items):
                try:
                    # 제목 추출
                    subj_div = item.find('div', class_='subj')
                    if not subj_div:
                        continue

                    title_link = subj_div.find('a')
                    if not title_link:
                        continue

                    title = title_link.get_text(strip=True)
                    logger.debug(f"항목 {item_idx + 1}: {title}")

                    # PDF 다운로드 링크 찾기
                    pdf_url = None

                    # 방법 1: 직접 FileDown.do 링크 찾기 (실적발표 페이지)
                    download_links = item.find_all('a', class_='btn-download')
                    for link in download_links:
                        href = link.get('href', '')
                        if 'FileDown.do' in href:
                            pdf_url = href
                            logger.debug(f"직접 다운로드 링크 발견: {pdf_url}")
                            break

                    # 방법 2: data-atchfileid 사용 (Fact Book 페이지)
                    if not pdf_url:
                        file_btn = item.find('a', attrs={'data-atchfileid': True})
                        if file_btn:
                            file_id = file_btn.get('data-atchfileid', '')
                            if file_id:
                                # 한국 eGov 표준 패턴으로 URL 생성
                                pdf_url = f"/cmm/fms/FileDown.do?fileId={file_id}&fileSeq=0"
                                logger.debug(f"파일 ID로 URL 생성: {pdf_url}")

                    if not pdf_url:
                        logger.warning(f"PDF 링크를 찾을 수 없음: {title}")
                        continue

                    # 상대 URL을 절대 URL로 변환
                    if pdf_url and not pdf_url.startswith('http'):
                        pdf_url = urljoin(BASE_URL, pdf_url)

                    # 날짜 추출
                    date_div = item.find('div', class_='date')
                    date_str = date_div.get_text(strip=True) if date_div else ''
                    date = self._parse_date(date_str) if date_str else ''

                    # 파일명 생성
                    filename = self._parse_quarter(title)

                    logger.info(f"✓ 항목 발견: {title} ({date})")

                    items.append({
                        'date': date,
                        'title': title,
                        'pdf_url': pdf_url,
                        'filename': filename,
                        'collected_at': datetime.now().isoformat()
                    })

                except Exception as e:
                    logger.warning(f"항목 {item_idx + 1} 파싱 중 오류: {str(e)}")
                    import traceback
                    logger.debug(traceback.format_exc())
                    continue

        logger.info(f"총 {len(items)}개 항목 수집 완료")
        return items

    def crawl(self) -> List[Dict]:
        """
        실적발표 페이지를 크롤링하여 데이터 수집

        Returns:
            게시글 정보 리스트
        """
        logger.info("실적발표 크롤링 시작")

        try:
            # WebDriver 초기화
            self._setup_driver()

            # 페이지 로드
            soup = self._fetch_page(self.url)
            if not soup:
                logger.error("페이지 로드 실패")
                return []

            # 항목 파싱
            items = self._parse_items(soup)

            if not items:
                logger.warning("수집된 항목이 없습니다. HTML 구조를 확인해주세요.")
                logger.info("HTML 구조 디버깅 정보:")
                logger.info(f"페이지 타이틀: {soup.title.string if soup.title else 'N/A'}")
                tables = soup.find_all('table')
                logger.info(f"테이블 개수: {len(tables)}")
                lists = soup.find_all(['ul', 'ol'])
                logger.info(f"리스트 개수: {len(lists)}")
            else:
                logger.info(f"{len(items)}개 항목 발견")

            return items

        finally:
            # WebDriver 종료
            if self.driver:
                self.driver.quit()
                logger.debug("WebDriver 종료")

    def save_to_csv(self, items: List[Dict]) -> bool:
        """
        수집한 데이터를 CSV 파일로 저장

        Args:
            items: 게시글 정보 리스트

        Returns:
            저장 성공 여부
        """
        if not items:
            logger.warning("저장할 데이터가 없습니다")
            return False

        try:
            # 디렉토리가 없으면 생성
            os.makedirs(DATA_DIR, exist_ok=True)

            df = pd.DataFrame(items, columns=CSV_COLUMNS)
            df.to_csv(EARNINGS_CSV, index=False, encoding='utf-8-sig')
            logger.info(f"{EARNINGS_CSV} 저장 완료 ({len(items)}개 항목)")
            return True

        except Exception as e:
            logger.error(f"CSV 저장 실패: {str(e)}")
            return False


def main():
    """테스트용 메인 함수"""
    logging.basicConfig(
        level=logging.INFO,
        format='[%(levelname)s] %(message)s'
    )

    crawler = EarningsCrawler()
    items = crawler.crawl()
    if items:
        crawler.save_to_csv(items)
        print(f"\n수집 완료: {len(items)}개")
        for item in items[:5]:  # 처음 5개만 출력
            print(f"  - {item['date']} | {item['title']}")


if __name__ == "__main__":
    main()
