"""
Fact Book 크롤러
"""
import re
import ssl
import time
import logging
import pandas as pd
import requests
import urllib3
from requests.adapters import HTTPAdapter
from urllib3.util.ssl_ import create_urllib3_context
from bs4 import BeautifulSoup
from datetime import datetime
from typing import List, Dict, Optional
from urllib.parse import urljoin

# SSL 인증서 검증 경고 비활성화
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from config import (
    FACTBOOK_URL, FACTBOOK_CSV, HEADERS,
    REQUEST_DELAY, MAX_RETRIES, TIMEOUT, CSV_COLUMNS, BASE_URL
)

logger = logging.getLogger(__name__)


class SSLAdapter(HTTPAdapter):
    """Legacy SSL renegotiation을 지원하는 커스텀 어댑터"""

    def init_poolmanager(self, *args, **kwargs):
        ctx = create_urllib3_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        # Legacy server 연결 허용
        ctx.options |= 0x4  # OP_LEGACY_SERVER_CONNECT
        kwargs['ssl_context'] = ctx
        return super().init_poolmanager(*args, **kwargs)


class FactBookCrawler:
    """Fact Book 크롤러 클래스"""

    def __init__(self):
        self.url = FACTBOOK_URL
        self.headers = HEADERS.copy()
        # SSL 어댑터가 적용된 세션 생성
        self.session = requests.Session()
        self.session.mount('https://', SSLAdapter())
        # 메인 페이지를 먼저 방문하여 쿠키 획득
        self._init_session()

    def _init_session(self):
        """
        세션 초기화: 메인 페이지를 방문하여 쿠키를 획득하고 실제 사용자처럼 행동
        """
        try:
            # 메인 페이지 방문
            main_url = "https://woorifg.com"
            logger.debug(f"메인 페이지 방문: {main_url}")
            response = self.session.get(
                main_url,
                headers=self.headers,
                timeout=TIMEOUT,
                verify=False,
                allow_redirects=True
            )
            # 약간의 딜레이 (사람처럼 행동)
            time.sleep(REQUEST_DELAY)

            # Referer 헤더 추가
            self.headers['Referer'] = main_url
            logger.debug("세션 초기화 완료")

        except Exception as e:
            logger.warning(f"세션 초기화 중 오류 (무시): {str(e)}")

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

        # 분기 정보를 찾을 수 없는 경우 날짜 기반으로 생성
        logger.warning(f"분기 정보 추출 실패, 제목 기반 파일명 생성: {title}")
        # 안전한 파일명 생성 (특수문자 제거)
        safe_title = re.sub(r'[^\w\s-]', '', title).strip()
        safe_title = re.sub(r'[-\s]+', '_', safe_title)
        return f"{safe_title[:50]}.pdf"  # 파일명 길이 제한

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

    def _fetch_page(self, url: str) -> Optional[BeautifulSoup]:
        """
        웹페이지를 가져와서 BeautifulSoup 객체로 반환

        Args:
            url: 크롤링할 URL

        Returns:
            BeautifulSoup 객체 또는 None
        """
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                logger.debug(f"페이지 요청 시도 ({attempt}/{MAX_RETRIES}): {url}")

                # 재시도 시 딜레이
                if attempt > 1:
                    time.sleep(REQUEST_DELAY * attempt)

                response = self.session.get(
                    url,
                    headers=self.headers,
                    timeout=TIMEOUT,
                    verify=False,
                    allow_redirects=True
                )
                response.raise_for_status()
                return BeautifulSoup(response.text, 'lxml')

            except requests.exceptions.RequestException as e:
                logger.warning(f"페이지 요청 실패 ({attempt}/{MAX_RETRIES}): {str(e)}")
                if attempt == MAX_RETRIES:
                    logger.error(f"페이지 요청 최종 실패: {url}")
                    return None

        return None

    def _parse_items(self, soup: BeautifulSoup) -> List[Dict]:
        """
        페이지에서 게시글 정보를 파싱

        주의: 실제 웹사이트 HTML 구조에 맞게 수정 필요

        Args:
            soup: BeautifulSoup 객체

        Returns:
            게시글 정보 리스트
        """
        items = []

        # 일반적인 IR 페이지 구조를 가정한 파싱
        # 실제 구조에 맞게 셀렉터 수정 필요
        # 예시 1: 테이블 구조
        table = soup.find('table', {'class': 'board-list'}) or soup.find('table')
        if table:
            rows = table.find_all('tr')[1:]  # 헤더 제외
            for row in rows:
                try:
                    cols = row.find_all('td')
                    if len(cols) < 2:
                        continue

                    # 제목과 링크 추출 (일반적으로 제목 컬럼에 있음)
                    title_col = cols[1] if len(cols) > 1 else cols[0]
                    link_tag = title_col.find('a')

                    if not link_tag:
                        continue

                    title = link_tag.get_text(strip=True)
                    pdf_url = link_tag.get('href', '')

                    # 상대 URL을 절대 URL로 변환
                    if pdf_url and not pdf_url.startswith('http'):
                        pdf_url = urljoin(self.url, pdf_url)

                    # 날짜 추출 (보통 마지막 컬럼)
                    date_col = cols[-1]
                    date_str = date_col.get_text(strip=True)
                    date = self._parse_date(date_str)

                    # 파일명 생성
                    filename = self._parse_quarter(title)

                    items.append({
                        'date': date,
                        'title': title,
                        'pdf_url': pdf_url,
                        'filename': filename,
                        'collected_at': datetime.now().isoformat()
                    })

                except Exception as e:
                    logger.warning(f"항목 파싱 중 오류: {str(e)}")
                    continue

        # 예시 2: 리스트(ul/li) 구조
        else:
            items_list = soup.find('ul', {'class': 'list'}) or soup.find('div', {'class': 'list'})
            if items_list:
                for item in items_list.find_all('li'):
                    try:
                        link = item.find('a')
                        if not link:
                            continue

                        title = link.get_text(strip=True)
                        pdf_url = link.get('href', '')

                        if pdf_url and not pdf_url.startswith('http'):
                            pdf_url = urljoin(self.url, pdf_url)

                        # 날짜는 다른 태그에서 추출
                        date_tag = item.find('span', {'class': 'date'}) or item.find('time')
                        date_str = date_tag.get_text(strip=True) if date_tag else ''
                        date = self._parse_date(date_str) if date_str else ''

                        filename = self._parse_quarter(title)

                        items.append({
                            'date': date,
                            'title': title,
                            'pdf_url': pdf_url,
                            'filename': filename,
                            'collected_at': datetime.now().isoformat()
                        })

                    except Exception as e:
                        logger.warning(f"항목 파싱 중 오류: {str(e)}")
                        continue

        return items

    def crawl(self) -> List[Dict]:
        """
        Fact Book 페이지를 크롤링하여 데이터 수집

        Returns:
            게시글 정보 리스트
        """
        logger.info("Fact Book 크롤링 시작")

        soup = self._fetch_page(self.url)
        if not soup:
            logger.error("페이지 로드 실패")
            return []

        items = self._parse_items(soup)

        if not items:
            logger.warning("수집된 항목이 없습니다. HTML 구조를 확인해주세요.")
            logger.info("HTML 구조 디버깅 정보:")
            logger.info(f"페이지 타이틀: {soup.title.string if soup.title else 'N/A'}")
            # 테이블 확인
            tables = soup.find_all('table')
            logger.info(f"테이블 개수: {len(tables)}")
            # 리스트 확인
            lists = soup.find_all(['ul', 'ol'])
            logger.info(f"리스트 개수: {len(lists)}")
        else:
            logger.info(f"{len(items)}개 항목 발견")

        return items

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
