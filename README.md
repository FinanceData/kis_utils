# KIS Utils
한국투자증권 API를 파이썬에서 쉽고 간편하게 사용할 수 있도록 도와주는 유틸리티 모듈로 CLI 인터페이스를 제공합니다.
접근 토큰 관리, 시세 조회, 잔고 확인 및 주문 기능을 간결한 인터페이스로 제공합니다.

비교적 간편한 유틸리티 라이브러리로 사용하거나 CLI로 사용이 가능합니다

## 🚀 시작하기

### 1. 환경 설정

### 2. .env 파일 설정
프로젝트 루트 디렉토리에 `.env.example` 파일을 복사하여 `.env` 파일을 생성하고 다음과 같이 환경 변수를 설정합니다.

```env
# 실행 환경 ("실전투자" 또는 "모의투자")
KIS_ENVIRONMENT="모의투자"

# 실전투자 정보
KIS_APP_KEY="YOUR_PROD_APP_KEY"
KIS_APP_SECRET="YOUR_PROD_APP_SECRET"
KIS_ACCOUNT="YOUR_ACCOUNT_NUMBER"
KIS_ACCOUNT_PROD="01"

# 모의투자 정보 (KIS_ENVIRONMENT="모의투자"인 경우 필수)
KIS_APP_KEY_VTS="YOUR_VTS_APP_KEY"
KIS_APP_SECRET_VTS="YOUR_VTS_APP_SECRET"
KIS_ACCOUNT_VTS="YOUR_VTS_ACCOUNT_NUMBER"
KIS_ACCOUNT_PROD_VTS="01"
```

## 주요 명령어
- `token`: 접근 토큰 신규 발급
- `price <종목코드>`: 현재가 정보 조회
- `daily <종목코드>`: 일/주/월 봉 데이터 조회
- `balance`: 계좌 잔고 및 보유 종목 조회
- `history`: 주문 및 체결 내역 조회
- `order`: 주식 주문 (매수/매도)
- `buyable <종목코드>`: 매수 가능 수량 조회

모든 명령어 뒤에 `--pretty`를 붙이면 한글 라벨이 포함된 가독성 좋은 화면을 볼 수 있습니다.

## CLI 사용법

가장 간편하게 `uv` 명령어를 사용하여 실행할 수 있습니다. (또는 `python -m kis_utils` 사용 가능)

```sh
# 현재가 조회 (기본 JSON 출력)
uv run kis-utils price 005930

# 사람이 읽기 좋은 포맷으로 조회
uv run kis-utils price 005930 --pretty

# 계좌 잔고 확인
uv run kis-utils balance --pretty

# 주식 주문 (삼성전자 1주 시장가 매수)
uv run kis-utils order 005930 -t buy -q 1 -p 0 -d 03
```

## uv tool 사용법
```sh
uv tool install kis-utils

# 설치 후
kis-utils price 005930 --pretty
kis-utils price 005930
kis-utils balance --pretty
```


##  기본 사용법
### 1. 접근 토큰 발급
```python
import kis_utils as kis

# 토큰 발급 (자동으로 파일에 저장 및 갱신됨)
access_token = kis.token()
```

### 2. 주식 시세 및 데이터 조회

#### 현재가 조회
```python
# 삼성전자 현재가 조회
df = kis.price("005930")
if not price_df.empty:
    current_price = int(price_df['stck_prpr'].iloc[0])
    print(f"현재가: {current_price:,}원")
```

#### 일봉 데이터 조회
```python
from datetime import datetime, timedelta

today = datetime.now()
start_date = (today - timedelta(days=30)).strftime("%Y%m%d")
end_date = today.strftime("%Y%m%d")

# 최근 30일 일봉 데이터
daily_data = kis.daily("005930")

# 주봉 데이터
weekly_data = kis.daily("005930", period="W")
```

### 3. 계좌 및 주문 관리

#### 계좌 잔고 조회
```python
balance = kis.balance()

# 예수금 확인
deposit = int(balance['output2'][0]['dnca_tot_amt'])

# 보유 종목 확인
for stock in balance['output1']:
    print(f"종목명: {stock['prdt_name']}, 보유수량: {stock['hldg_qty']}")
```

#### 주문 내역 조회
```python
# 최근 7일간 주문 내역 조회
history = kis.order_history(start_date, end_date)
```

#### 주식 주문
```python
# 삼성전자 1주 시장가 매수
result = kis.buy(
    stock_code="005930",
    quantity=1,
    price=0,               # 시장가인 경우 0
    order_division="03"    # 01: 지정가, 03: 시장가
)

# 삼성전자 1주 지정가 매도
result = kis.sell(
    stock_code="005930",
    quantity=1,
    price=70000,
    order_division="01"
)
```

## 📝 참고 사항

- **토큰 자동 관리**: 발급된 토큰은 `.access_token` 파일에 자동 저장되며, 만료 전 호출 시 기존 토큰을 재사용하거나 필요시 자동 갱신합니다.
- **오류 처리**: API 호출 실패 시 관련 에러 메시지를 출력하며, 네트워크 상태나 앱 키 설정을 확인해야 합니다.
- **주문 주의**: `place_order` 함수는 실제 거래를 발생시키므로, 충분한 테스트 후에 실전 투자에 사용하시기 바랍니다.

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.
