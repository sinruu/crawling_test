"""
HTML 구조 확인을 위한 디버그 스크립트
"""
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium_stealth import stealth
from webdriver_manager.chrome import ChromeDriverManager

def save_page_html(url, output_file):
    """페이지 HTML을 파일로 저장"""
    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--ignore-certificate-errors')
    options.add_argument('--allow-insecure-localhost')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    stealth(driver,
            languages=["ko-KR", "ko", "en-US", "en"],
            vendor="Google Inc.",
            platform="Win32",
            webgl_vendor="Intel Inc.",
            renderer="Intel Iris OpenGL Engine",
            fix_hairline=True,
            )

    try:
        # 메인 페이지 먼저 방문
        print("메인 페이지 방문 중...")
        driver.get("https://www.woorifg.com/kor/main/index.do")
        time.sleep(2)

        # 타겟 페이지 방문
        print(f"타겟 페이지 방문 중: {url}")
        driver.get(url)
        time.sleep(3)

        # HTML 저장
        html = driver.page_source
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html)

        print(f"HTML 저장 완료: {output_file}")
        print(f"페이지 타이틀: {driver.title}")

    finally:
        driver.quit()

if __name__ == "__main__":
    # 실적발표 페이지
    save_page_html(
        "https://www.woorifg.com/kor/investor/ir/earnings-announcement/list.do",
        "earnings_page.html"
    )

    # Fact Book 페이지
    save_page_html(
        "https://www.woorifg.com/kor/investor/ir/fact-book/list.do",
        "factbook_page.html"
    )

    print("\n완료! earnings_page.html과 factbook_page.html을 확인하세요.")
