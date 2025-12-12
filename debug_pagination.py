"""
페이지네이션 디버깅 스크립트
"""
import logging
from crawler.factbook import FactBookCrawler
from bs4 import BeautifulSoup

# 디버그 레벨 로깅 설정
logging.basicConfig(
    level=logging.DEBUG,
    format='[%(levelname)s] %(message)s'
)

logger = logging.getLogger(__name__)

def debug_pagination():
    """페이지네이션 구조 확인"""
    crawler = FactBookCrawler()

    try:
        # WebDriver 초기화
        crawler._setup_driver()

        # 첫 페이지 로드
        soup = crawler._fetch_page(crawler.url)

        # 페이지네이션 div 찾기
        paging_div = soup.find('div', class_='paging')

        if paging_div:
            logger.info("✓ 페이지네이션 div 발견!")
            logger.info(f"HTML: {paging_div.prettify()[:500]}")

            # data-page 속성을 가진 링크 찾기
            page_links = paging_div.find_all('a', attrs={'data-page': True})
            logger.info(f"✓ data-page 링크 개수: {len(page_links)}")

            for link in page_links:
                page_num = link.get('data-page')
                logger.info(f"  - 페이지 {page_num}: {link}")

            # 최대 페이지 번호
            if page_links:
                max_page = max(int(link.get('data-page', 1)) for link in page_links)
                logger.info(f"✓ 최대 페이지: {max_page}")
            else:
                logger.warning("✗ data-page 속성을 가진 링크가 없음")
        else:
            logger.warning("✗ 페이지네이션 div를 찾을 수 없음")

            # 대안으로 찾아보기
            logger.info("대안 검색 중...")
            all_divs = soup.find_all('div')
            logger.info(f"총 div 개수: {len(all_divs)}")

            # 'page' 또는 'paging' 관련 div 찾기
            for div in all_divs:
                classes = div.get('class', [])
                if any('pag' in str(c).lower() for c in classes):
                    logger.info(f"페이지 관련 div 발견: class={classes}")
                    logger.info(f"  HTML: {str(div)[:200]}")

    finally:
        if crawler.driver:
            crawler.driver.quit()

if __name__ == "__main__":
    debug_pagination()
