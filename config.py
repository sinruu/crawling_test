"""
우리금융 IR 크롤러 설정 파일
"""
import os

# 기본 URL 설정
BASE_URL = "https://woorifg.com/kor/investor/ir"
EARNINGS_URL = f"{BASE_URL}/earnings/list.do"
FACTBOOK_URL = f"{BASE_URL}/fact-book/list.do"

# 디렉토리 설정
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DOWNLOAD_DIR = os.path.join(DATA_DIR, "downloads")
EARNINGS_DOWNLOAD_DIR = os.path.join(DOWNLOAD_DIR, "earnings")
FACTBOOK_DOWNLOAD_DIR = os.path.join(DOWNLOAD_DIR, "factbook")

# CSV 파일 경로
EARNINGS_CSV = os.path.join(DATA_DIR, "earnings.csv")
FACTBOOK_CSV = os.path.join(DATA_DIR, "factbook.csv")

# HTTP 요청 설정
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
    'Accept-Encoding': 'gzip, deflate, br, zstd',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Sec-Fetch-User': '?1',
    'sec-ch-ua': '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
    'Cache-Control': 'max-age=0',
}

# 크롤링 설정
REQUEST_DELAY = 0.5  # 요청 간 딜레이 (초)
MAX_RETRIES = 3  # 최대 재시도 횟수
TIMEOUT = 30  # 요청 타임아웃 (초)

# CSV 컬럼 정의
CSV_COLUMNS = ['date', 'title', 'pdf_url', 'filename', 'collected_at']
