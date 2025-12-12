"""
Fact Book 크롤러 (selenium-stealth 기반)
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
    FACTBOOK_URL, FACTBOOK_CSV, BASE_URL, DATA_DIR,
    REQUEST_DELAY, MAX_RETRIES, CSV_COLUMNS,
    HEADLESS, PAGE_LOAD_TIMEOUT, IMPLICIT_WAIT
)

logger = logging.getLogger(__name__)


class FactBookCrawler:
    """Fact Book 크롤러 클래스 (Selenium 기반)"""

    def __init__(self):
        self.url = FACTBOOK_URL
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
            파일명 (예: "2025_3Q_FactBook.pdf") 또는 None
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
                return f"{year}_{quarter}Q_FactBook.pdf"

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

    def _get_excel_url_from_view(self, view_url: str) -> Optional[str]:
        """
        view.do 페이지를 방문하여 Excel 파일 다운로드 URL 추출

        Args:
            view_url: view.do 페이지 URL

        Returns:
            Excel 파일 다운로드 URL 또는 None
        """
        try:
            # 상대 URL을 절대 URL로 변환
            # list.do 페이지의 URL을 기준으로 상대 경로 해석
            full_url = urljoin(self.url, view_url)
            logger.debug(f"View 페이지 방문: {full_url}")

            # 페이지 로드
            self.driver.get(full_url)
            time.sleep(REQUEST_DELAY * 2)

            # 페이지 소스 파싱
            soup = BeautifulSoup(self.driver.page_source, 'lxml')

            # Excel 파일 링크 찾기 (.xlsx 파일)
            links = soup.find_all('a', href=True)
            for link in links:
                href = link.get('href', '')
                text = link.get_text(strip=True)

                # .xlsx 파일이면서 FileDown.do 링크인 경우
                if '.xlsx' in text.lower() or '.xlsx' in href:
                    if 'FileDown.do' in href:
                        logger.debug(f"Excel 파일 발견: {text} -> {href}")
                        return href

            logger.warning(f"Excel 파일을 찾을 수 없음: {full_url}")
            return None

        except Exception as e:
            logger.error(f"View 페이지 파싱 오류: {str(e)}")
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
                    view_url = title_link.get('href', '')
                    logger.debug(f"항목 {item_idx + 1}: {title}")

                    # View 페이지에서 Excel 파일 URL 가져오기
                    excel_url = None
                    if view_url:
                        excel_url = self._get_excel_url_from_view(view_url)

                    if not excel_url:
                        logger.warning(f"Excel 파일을 찾을 수 없음: {title}")
                        continue

                    # 상대 URL을 절대 URL로 변환
                    if excel_url and not excel_url.startswith('http'):
                        excel_url = urljoin(BASE_URL, excel_url)

                    # 날짜 추출
                    date_div = item.find('div', class_='date')
                    date_str = date_div.get_text(strip=True) if date_div else ''
                    date = self._parse_date(date_str) if date_str else ''

                    # Excel 파일명 추출 (URL에서)
                    filename = None
                    if 'saveFileNm=' in excel_url:
                        # saveFileNm 파라미터에서 파일명 추출
                        import re
                        match = re.search(r'saveFileNm=([^&]+)', excel_url)
                        if match:
                            filename = match.group(1)

                    # 파일명이 없으면 기본 생성
                    if not filename:
                        filename = self._parse_quarter(title)

                    logger.info(f"✓ 항목 발견: {title} ({date}) - {filename}")

                    items.append({
                        'date': date,
                        'title': title,
                        'pdf_url': excel_url,  # Excel URL을 pdf_url 컬럼에 저장 (하위 호환성)
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

    def _get_total_pages(self, soup: BeautifulSoup) -> int:
        """
        페이지네이션 정보에서 전체 페이지 수 추출

        Args:
            soup: BeautifulSoup 객체

        Returns:
            전체 페이지 수
        """
        try:
            paging_div = soup.find('div', class_='paging')
            if not paging_div:
                logger.debug("페이지네이션 요소를 찾을 수 없음")
                return 1

            # data-page 속성을 가진 모든 링크 찾기
            page_links = paging_div.find_all('a', attrs={'data-page': True})
            if not page_links:
                logger.debug("페이지 링크를 찾을 수 없음")
                return 1

            # 가장 큰 페이지 번호 찾기
            max_page = max(int(link.get('data-page', 1)) for link in page_links)
            logger.info(f"전체 페이지 수: {max_page}")
            return max_page

        except Exception as e:
            logger.warning(f"페이지 수 파싱 실패: {str(e)}")
            return 1

    def _navigate_to_page(self, page_num: int) -> Optional[BeautifulSoup]:
        """
        특정 페이지로 이동하여 BeautifulSoup 객체 반환

        Args:
            page_num: 이동할 페이지 번호

        Returns:
            BeautifulSoup 객체 또는 None
        """
        try:
            logger.info(f"페이지 {page_num}로 이동 중...")

            # view.do 페이지 방문 후 목록 페이지로 돌아오기
            logger.debug(f"목록 페이지로 복귀: {self.url}")
            self.driver.get(self.url)
            time.sleep(REQUEST_DELAY * 2)

            # 페이지 번호에 해당하는 링크 찾기 및 클릭
            page_link = self.driver.find_element(By.CSS_SELECTOR, f'a[data-page="{page_num}"]')
            page_link.click()

            # 페이지 로딩 대기
            time.sleep(REQUEST_DELAY * 3)

            # 페이지 소스 파싱
            page_source = self.driver.page_source
            return BeautifulSoup(page_source, 'lxml')

        except Exception as e:
            logger.error(f"페이지 {page_num} 이동 실패: {str(e)}")
            return None

    def crawl(self) -> List[Dict]:
        """
        Fact Book 페이지를 크롤링하여 데이터 수집 (모든 페이지)

        Returns:
            게시글 정보 리스트
        """
        logger.info("Fact Book 크롤링 시작")

        try:
            # WebDriver 초기화
            self._setup_driver()

            # 첫 번째 페이지 로드
            soup = self._fetch_page(self.url)
            if not soup:
                logger.error("페이지 로드 실패")
                return []

            # 전체 페이지 수 확인
            total_pages = self._get_total_pages(soup)

            # 모든 항목을 저장할 리스트
            all_items = []

            # 첫 번째 페이지 항목 파싱
            logger.info(f"페이지 1/{total_pages} 파싱 중...")
            items = self._parse_items(soup)
            all_items.extend(items)
            logger.info(f"페이지 1: {len(items)}개 항목 수집")

            # 2페이지 이상인 경우 나머지 페이지 처리
            if total_pages > 1:
                for page_num in range(2, total_pages + 1):
                    logger.info(f"페이지 {page_num}/{total_pages} 파싱 중...")

                    # 페이지 이동
                    soup = self._navigate_to_page(page_num)
                    if not soup:
                        logger.warning(f"페이지 {page_num} 로드 실패, 건너뜀")
                        continue

                    # 항목 파싱
                    items = self._parse_items(soup)
                    all_items.extend(items)
                    logger.info(f"페이지 {page_num}: {len(items)}개 항목 수집")

                    # 요청 간 딜레이
                    time.sleep(REQUEST_DELAY)

            if not all_items:
                logger.warning("수집된 항목이 없습니다. HTML 구조를 확인해주세요.")
                logger.info("HTML 구조 디버깅 정보:")
                logger.info(f"페이지 타이틀: {soup.title.string if soup.title else 'N/A'}")
                tables = soup.find_all('table')
                logger.info(f"테이블 개수: {len(tables)}")
                lists = soup.find_all(['ul', 'ol'])
                logger.info(f"리스트 개수: {len(lists)}")
            else:
                logger.info(f"총 {len(all_items)}개 항목 수집 완료 ({total_pages}페이지)")

            return all_items

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
            df.to_csv(FACTBOOK_CSV, index=False, encoding='utf-8-sig')
            logger.info(f"{FACTBOOK_CSV} 저장 완료 ({len(items)}개 항목)")
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

    crawler = FactBookCrawler()
    items = crawler.crawl()
    if items:
        crawler.save_to_csv(items)
        print(f"\n수집 완료: {len(items)}개")
        for item in items[:5]:  # 처음 5개만 출력
            print(f"  - {item['date']} | {item['title']}")


if __name__ == "__main__":
    main()
