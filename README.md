# KIS Utils

한국투자증권 API를 파이썬에서 쉽고 간편하게 사용할 수 있도록 도와주는 유틸리티 모듈입니다. 
접근 토큰 관리, 시세 조회, 잔고 확인 및 주문 기능을 간결한 인터페이스로 제공합니다.

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

## 💡 기본 사용법
### 1. 접근 토큰 발급
```python
import kis_utils as kis

# 접근 토큰 발급 (자동으로 .access_token 파일에 저장 및 관리됨)
access_token = kis.issue_access_token()
```

### 2. 주식 시세 및 데이터 조회

#### 현재가 조회
```python
# 삼성전자(005930) 현재가 조회 (DataFrame 반환)
price_df = kis.get_stock_price("005930")
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

# 최근 30일 일봉 데이터 조회
daily_data = kis.get_daily_stock_data("005930", start_date, end_date)
```

### 3. 계좌 및 주문 관리

#### 계좌 잔고 조회
```python
balance = kis.account_balance()

# 예수금 확인
deposit = int(balance['output2'][0]['dnca_tot_amt'])

# 보유 종목 확인
for stock in balance['output1']:
    print(f"종목명: {stock['prdt_name']}, 보유수량: {stock['hldg_qty']}")
```

#### 주문 내역 조회
```python
# 최근 7일간 주문 내역 조회
history = kis.account_order_history(start_date, end_date)
```

#### 주식 주문
```python
# 삼성전자 1주 시장가 매수
result = kis.place_order(
    stock_code="005930",
    order_type="2",        # 1: 매도, 2: 매수
    quantity=1,
    price=0,               # 시장가인 경우 0
    order_division="03"    # 01: 지정가, 03: 시장가
)
```

## 📝 참고 사항

- **토큰 자동 관리**: 발급된 토큰은 `.access_token` 파일에 자동 저장되며, 만료 전 호출 시 기존 토큰을 재사용하거나 필요시 자동 갱신합니다.
- **오류 처리**: API 호출 실패 시 관련 에러 메시지를 출력하며, 네트워크 상태나 앱 키 설정을 확인해야 합니다.
- **주문 주의**: `place_order` 함수는 실제 거래를 발생시키므로, 충분한 테스트 후에 실전 투자에 사용하시기 바랍니다.

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.
