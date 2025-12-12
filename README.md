# 우리금융 IR 크롤러

우리금융그룹 IR 페이지에서 **실적발표**와 **Fact Book** PDF 자료를 자동으로 수집하는 크롤러입니다.

## 기능

- 실적발표 자료 메타데이터 수집 및 CSV 저장
- Fact Book 자료 메타데이터 수집 및 CSV 저장
- PDF 파일 자동 다운로드 (선택적)
- 중복 파일 자동 스킵
- 네트워크 오류 시 자동 재시도 (최대 3회)
- 서버 부하 방지를 위한 요청 간 딜레이

## 설치

### 1. 저장소 클론

```bash
git clone https://github.com/sinruu/crawling_test.git
cd crawling_test
```

### 2. 의존성 설치

```bash
pip install -r requirements.txt
```

## 사용 방법

### 기본 사용법

```bash
# 메타데이터만 수집 (CSV 저장)
python main.py

# PDF까지 다운로드
python main.py --download

# 실적발표만 크롤링
python main.py --type earnings

# Fact Book만 크롤링
python main.py --type factbook

# PDF 다운로드 + 상세 로그
python main.py --download --verbose
```

### 명령행 옵션

| 옵션 | 축약형 | 설명 |
|------|--------|------|
| `--download` | `-d` | PDF 파일도 다운로드 |
| `--type {earnings,factbook,all}` | `-t` | 크롤링 대상 선택 (기본값: all) |
| `--verbose` | `-v` | 상세 로그 출력 |
| `--help` | `-h` | 도움말 표시 |

### 사용 예시

```bash
# 모든 자료의 메타데이터만 수집
python main.py

# 실적발표 PDF만 다운로드
python main.py -t earnings -d

# 모든 자료 다운로드 (상세 로그)
python main.py -d -v
```

## 프로젝트 구조

```
crawling_test/
├── main.py                     # 메인 실행 파일
├── config.py                   # 설정 파일
├── requirements.txt            # Python 패키지 의존성
├── .gitignore                  # Git 제외 파일 목록
├── README.md                   # 프로젝트 문서
│
├── crawler/                    # 크롤러 모듈
│   ├── __init__.py
│   ├── earnings.py             # 실적발표 크롤러
│   └── factbook.py             # Fact Book 크롤러
│
├── utils/                      # 유틸리티 모듈
│   ├── __init__.py
│   └── downloader.py           # PDF 다운로드 유틸
│
└── data/                       # 데이터 저장 디렉토리
    ├── earnings.csv            # 실적발표 메타데이터
    ├── factbook.csv            # Fact Book 메타데이터
    └── downloads/              # PDF 다운로드 디렉토리
        ├── earnings/           # 실적발표 PDF
        └── factbook/           # Fact Book PDF
```

## 출력 데이터

### CSV 파일 형식

`data/earnings.csv` 및 `data/factbook.csv`

| 컬럼 | 설명 | 예시 |
|------|------|------|
| `date` | 게시일 | 2025.10.29 |
| `title` | 제목 | 2025년 3분기 Fact Book |
| `pdf_url` | PDF 다운로드 URL | https://woorifg.com/... |
| `filename` | 저장 파일명 | 2025_3Q_FactBook.pdf |
| `collected_at` | 수집 시간 (ISO 8601) | 2025-12-12T10:30:00 |

### 파일명 형식

- **실적발표**: `YYYY_NQ_실적발표.pdf` (예: `2025_3Q_실적발표.pdf`)
- **Fact Book**: `YYYY_NQ_FactBook.pdf` (예: `2025_3Q_FactBook.pdf`)

## 설정

`config.py`에서 다음 설정을 변경할 수 있습니다:

```python
# 크롤링 설정
REQUEST_DELAY = 0.5     # 요청 간 딜레이 (초)
MAX_RETRIES = 3         # 최대 재시도 횟수
TIMEOUT = 30            # 요청 타임아웃 (초)

# URL 설정
EARNINGS_URL = "..."    # 실적발표 페이지 URL
FACTBOOK_URL = "..."    # Fact Book 페이지 URL
```

## 주의사항

### 웹 크롤링 에티켓

1. **robots.txt 확인**: 크롤링 전 사이트의 robots.txt를 확인하세요
2. **적절한 딜레이**: 기본 설정(0.5초)을 유지하여 서버 부하를 방지하세요
3. **User-Agent 설정**: 적절한 User-Agent 헤더를 사용합니다
4. **법적 책임**: 수집한 데이터의 사용은 사용자의 책임입니다

### HTML 구조 변경 대응

웹사이트 구조가 변경되면 크롤러가 작동하지 않을 수 있습니다. 이 경우:

1. 상세 로그 모드로 실행하여 오류 확인:
   ```bash
   python main.py -v
   ```

2. `crawler/earnings.py` 또는 `crawler/factbook.py`의 `_parse_items()` 메서드 수정

3. 웹사이트의 실제 HTML 구조에 맞게 셀렉터 조정

### 에러 처리

크롤러는 다음과 같이 오류를 처리합니다:

- **네트워크 오류**: 3회 재시도 후 로그 남기고 스킵
- **파일 중복**: 이미 존재하면 다운로드 건너뛰기
- **파싱 실패**: 해당 항목 건너뛰고 다음 진행
- **빈 리스트**: 정상 완료로 처리 (로그만 남김)

## 로그 예시

```
[INFO] 우리금융 IR 크롤러 v1.0
[INFO] ============================================================
[INFO] 실적발표 크롤링 시작
[INFO] ============================================================
[INFO] 5개 항목 발견
[INFO] data/earnings.csv 저장 완료 (5개 항목)
[INFO]
[INFO] PDF 다운로드 시작
[INFO] ------------------------------------------------------------
[INFO] PDF 다운로드 시작 (5개)
[SUCCESS] 2025_3Q_실적발표.pdf 다운로드 완료 (1,234,567 bytes)
[SKIP] 2025_2Q_실적발표.pdf 이미 존재
[SUCCESS] 2025_1Q_실적발표.pdf 다운로드 완료 (1,123,456 bytes)
[INFO] ------------------------------------------------------------
[INFO] 다운로드 완료 - 성공: 2, 실패: 0, 건너뜀: 3
[INFO] ============================================================
[INFO] 실적발표 크롤링 완료
[INFO] ============================================================
```

## 트러블슈팅

### PDF 다운로드 실패

```
[ERROR] 2025_3Q_실적발표.pdf 다운로드 실패: Timeout
```

**해결 방법**:
- `config.py`에서 `TIMEOUT` 값을 늘려보세요 (예: 60초)
- 네트워크 연결 상태를 확인하세요

### 수집된 항목이 없음

```
[WARNING] 수집된 항목이 없습니다. HTML 구조를 확인해주세요.
```

**해결 방법**:
1. 웹사이트가 정상적으로 접근 가능한지 확인
2. 상세 로그 모드(`-v`)로 실행하여 HTML 구조 확인
3. 필요시 크롤러 코드의 파싱 로직 수정

### 403 Forbidden 오류

```
[ERROR] 페이지 요청 최종 실패: https://...
```

**해결 방법**:
- 웹사이트에서 크롤링을 차단했을 수 있습니다
- `config.py`의 `HEADERS`를 수정하여 다른 User-Agent 시도
- 브라우저에서 직접 접속이 가능한지 확인

## 개발

### 개별 모듈 테스트

```bash
# 실적발표 크롤러만 테스트
python -m crawler.earnings

# Fact Book 크롤러만 테스트
python -m crawler.factbook
```

### 코드 스타일

- Python PEP 8 준수
- 함수/클래스에 docstring 작성
- 타입 힌트 사용 권장

## 라이선스

이 프로젝트는 교육 및 개인 사용 목적으로 제작되었습니다. 수집한 데이터의 사용은 우리금융그룹의 이용약관을 준수해야 합니다.

## 기여

버그 리포트나 기능 제안은 Issues를 통해 제출해주세요.

## 변경 이력

### v1.0 (2025-12-12)
- 초기 릴리스
- 실적발표 크롤러 구현
- Fact Book 크롤러 구현
- PDF 다운로드 기능
- CSV 저장 기능
