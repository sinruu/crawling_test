"""
View 페이지에서 Excel 파일 링크를 찾기 위한 스크립트
"""
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium_stealth import stealth
from webdriver_manager.chrome import ChromeDriverManager
import time

options = Options()
options.add_argument('--headless=new')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
options.add_argument('--ignore-certificate-errors')

service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=options)

stealth(driver,
        languages=['ko-KR', 'ko'],
        vendor='Google Inc.',
        platform='Win32',
        webgl_vendor='Intel Inc.',
        renderer='Intel Iris OpenGL Engine',
        fix_hairline=True)

try:
    # 메인 페이지 먼저 방문
    print("메인 페이지 방문 중...")
    driver.get('https://www.woorifg.com/kor/main/index.do')
    time.sleep(2)

    # 2025년 3분기 Fact Book view 페이지 방문
    print("2025년 3분기 Fact Book view 페이지 방문 중...")
    driver.get('https://www.woorifg.com/kor/investor/ir/fact-book/view.do?seq=1106')
    time.sleep(3)

    # 페이지 소스 저장
    with open('factbook_view_page.html', 'w', encoding='utf-8') as f:
        f.write(driver.page_source)

    print(f'✓ View 페이지 저장 완료: factbook_view_page.html')
    print(f'✓ 페이지 타이틀: {driver.title}')

    # Excel 파일 링크 찾기
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(driver.page_source, 'html.parser')

    print("\n=== 다운로드 링크 찾기 ===")

    # FileDown.do 링크 모두 찾기
    links = soup.find_all('a', href=True)
    for link in links:
        href = link.get('href', '')
        if 'FileDown.do' in href or 'download' in href.lower():
            text = link.get_text(strip=True)
            print(f"링크: {href}")
            print(f"텍스트: {text}")
            print("---")

finally:
    driver.quit()
