"""
한국투자증권 API 유틸리티 모듈
"""
import json
import os
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

import requests
import pandas as pd
from dotenv import load_dotenv

# 로깅 설정
logger = logging.getLogger(__name__)

# .env 파일 로드
load_dotenv()

# 환경변수 읽기
KIS_ENVIRONMENT = os.getenv('KIS_ENVIRONMENT', '모의투자')

if KIS_ENVIRONMENT == '실전투자':
    APP_KEY = os.getenv('KIS_APP_KEY')
    APP_SECRET = os.getenv('KIS_APP_SECRET')
    ACCOUNT = os.getenv('KIS_ACCOUNT')
    ACCOUNT_PROD = os.getenv('KIS_ACCOUNT_PROD')
    BASE_URL = os.getenv('KIS_BASE_URL', 'https://openapi.koreainvestment.com:9443')
    WS_URL = os.getenv('KIS_WS_URL', 'ws://ops.koreainvestment.com:21000')
else:  # 모의투자
    APP_KEY = os.getenv('KIS_APP_KEY_VTS')
    APP_SECRET = os.getenv('KIS_APP_SECRET_VTS')
    ACCOUNT = os.getenv('KIS_ACCOUNT_VTS')
    ACCOUNT_PROD = os.getenv('KIS_ACCOUNT_PROD_VTS')
    BASE_URL = os.getenv('KIS_BASE_URL_VTS', 'https://openapivts.koreainvestment.com:29443')
    WS_URL = os.getenv('KIS_WS_URL_VTS', 'ws://ops.koreainvestment.com:31000')

# 계좌 정보 검증
if not ACCOUNT or not ACCOUNT.strip():
    raise ValueError(
        f"계좌번호가 설정되지 않았습니다. "
        f".env 파일에 {'KIS_ACCOUNT' if KIS_ENVIRONMENT == '실전투자' else 'KIS_ACCOUNT_VTS'}를 설정하세요."
    )
if not ACCOUNT_PROD or not ACCOUNT_PROD.strip():
    raise ValueError(
        f"계좌상품코드가 설정되지 않았습니다. "
        f".env 파일에 {'KIS_ACCOUNT_PROD' if KIS_ENVIRONMENT == '실전투자' else 'KIS_ACCOUNT_PROD_VTS'}를 설정하세요."
    )

# 계좌번호를 문자열로 변환 (앞뒤 공백 제거)
ACCOUNT = str(ACCOUNT).strip()
ACCOUNT_PROD = str(ACCOUNT_PROD).strip()

# 토큰 파일 경로
_TOKEN_FILE = ".access_token"

# 요청 횟수 제한 관리를 위한 변수
_request_count = 0


def _load_token_from_file() -> Optional[Dict]:
    """파일에서 토큰 정보 로드"""
    if not os.path.exists(_TOKEN_FILE):
        return None
    
    try:
        with open(_TOKEN_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        logger.warning(f"토큰 파일 읽기 실패: {str(e)}")
        return None


def _save_token_to_file(token_data: Dict, expiry_time: datetime):
    """토큰 정보를 파일에 저장"""
    try:
        token_info = {
            "access_token": token_data.get("access_token"),
            "expires_at": expiry_time.strftime("%Y-%m-%d %H:%M:%S"),
            "token_type": token_data.get("token_type", "Bearer")
        }
        with open(_TOKEN_FILE, 'w', encoding='utf-8') as f:
            json.dump(token_info, f, ensure_ascii=False, indent=2)
    except IOError as e:
        logger.error(f"토큰 파일 저장 실패: {str(e)}")
        raise


def _get_access_token() -> str:
    """유효한 토큰 반환, 필요시 갱신"""
    current_time = datetime.now()

    # 파일에서 토큰 로드
    token_info = _load_token_from_file()
    
    if token_info:
        access_token = token_info.get("access_token")
        expires_at_str = token_info.get("expires_at")
        
        if access_token and expires_at_str:
            try:
                expiry_time = datetime.strptime(expires_at_str, "%Y-%m-%d %H:%M:%S")
                # 토큰이 유효하고 만료 예정이 아닌 경우(30분 이내) 반환
                if current_time + timedelta(minutes=30) < expiry_time:
                    return access_token
            except ValueError:
                logger.warning("토큰 만료 시간 파싱 실패, 토큰 갱신")
    
    # 토큰이 없거나 만료 예정인 경우 갱신
    _refresh_token()
    
    # 갱신 후 다시 로드
    token_info = _load_token_from_file()
    if token_info and token_info.get("access_token"):
        return token_info["access_token"]
    else:
        raise Exception("토큰 발급 및 저장 실패")


def _refresh_token():
    """토큰 갱신"""
    url = f"{BASE_URL}/oauth2/tokenP"

    headers = {
        "Content-Type": "application/json"
    }

    body = {
        "grant_type": "client_credentials",
        "appkey": APP_KEY,
        "appsecret": APP_SECRET
    }

    response = requests.post(url, headers=headers, data=json.dumps(body))

    if response.status_code == 200:
        token_data = response.json()

        # 만료 시간 파싱 및 설정
        expires_at_str = token_data.get("access_token_token_expired")
        if expires_at_str:
            expiry_time = datetime.strptime(expires_at_str, "%Y-%m-%d %H:%M:%S")
        else:
            # 만료 시간 정보가 없는 경우 현재 시간 + expires_in(초)로 설정
            expires_in = token_data.get("expires_in", 86400)  # 기본값 24시간
            expiry_time = datetime.now() + timedelta(seconds=expires_in)
        
        # 파일에 저장
        _save_token_to_file(token_data, expiry_time)
    else:
        raise Exception(f"토큰 갱신 실패: {response.text}")


def _generate_hashkey(request_body: Dict[str, Any]) -> str:
    """요청 본문으로 해시키 생성"""
    url = f"{BASE_URL}/uapi/hashkey"

    headers = {
        "content-type": "application/json",
        "appkey": APP_KEY,
        "appsecret": APP_SECRET
    }

    try:
        response = requests.post(url, headers=headers, data=json.dumps(request_body))

        if response.status_code == 200:
            hash_key = response.json()["HASH"]
            logger.debug(f"해시키 생성 완료: {hash_key}")
            return hash_key
        else:
            logger.error(f"해시키 생성 실패 (HTTP {response.status_code}): {response.text}")
            raise Exception(f"해시키 생성 실패: {response.text}")

    except Exception as e:
        logger.error(f"해시키 생성 중 예외 발생: {str(e)}")
        raise Exception(f"해시키 생성 중 예외 발생: {str(e)}")


def _api_request(method: str, endpoint: str, tr_id: str, params: Optional[Dict] = None,
                data: Optional[Dict] = None, headers: Optional[Dict] = None, use_hashkey: bool = False):
    """API 요청 함수"""
    global _request_count
    
    # 접근 토큰 획득
    access_token = _get_access_token()

    # 요청 URL 구성
    url = f"{BASE_URL}{endpoint}"

    # 기본 헤더 설정
    default_headers = {
        "content-type": "application/json",
        "authorization": f"Bearer {access_token}",
        "appkey": APP_KEY,
        "appsecret": APP_SECRET,
        "tr_id": tr_id
    }

    # 추가 헤더 병합
    if headers:
        default_headers.update(headers)

    # 해시키 생성 및 추가 (POST 요청 및 use_hashkey가 True인 경우)
    if method.upper() == 'POST' and data and use_hashkey:
        try:
            hashkey = _generate_hashkey(data)
            default_headers["hashkey"] = hashkey
        except Exception as e:
            logger.error(f"해시키 생성 실패: {str(e)}")
            raise

    # 요청 횟수 증가
    _request_count += 1

    try:
        # HTTP 요청 실행
        if method.upper() == 'GET':
            response = requests.get(url, params=params, headers=default_headers)
        elif method.upper() == 'POST':
            response = requests.post(url, headers=default_headers, data=json.dumps(data))
        else:
            raise ValueError(f"지원하지 않는 HTTP 메소드: {method}")

        # 응답 상태 코드 확인
        if response.status_code == 200:
            result = response.json()

            # API 응답 코드 확인
            if result.get('rt_cd') == '0':  # 정상 응답
                logger.debug(f"API 요청 성공: {tr_id}")
                return result
            else:
                error_msg = f"API 오류 (RT_CD: {result.get('rt_cd')}): {result.get('msg1')}"
                logger.error(error_msg)
                raise Exception(error_msg)
        else:
            error_msg = f"HTTP 오류 (HTTP {response.status_code}): {response.text}"
            logger.error(error_msg)
            raise Exception(error_msg)

    except requests.exceptions.RequestException as e:
        logger.error(f"요청 예외 발생: {str(e)}")
        raise


def issue_access_token() -> str:
    """접근토큰 신규 발급"""
    # 토큰 갱신 (파일에 저장됨)
    _refresh_token()
    
    # 파일에서 토큰 읽기
    token_info = _load_token_from_file()
    if token_info and token_info.get("access_token"):
        token = token_info["access_token"]
        # 환경변수에도 저장
        if KIS_ENVIRONMENT == '실전투자':
            os.environ['KIS_ACCESS_TOKEN'] = token
        else:
            os.environ['KIS_ACCESS_TOKEN_VTS'] = token
        return token
    else:
        raise Exception("토큰 발급 실패")


def issue_hashkey(request_body: Dict[str, Any]) -> str:
    """해시키 발급"""
    return _generate_hashkey(request_body)


def get_stock_price(stock_code: str, market_code: str = "J"):
    """주식 현재가 조회 (DataFrame 반환)"""
    endpoint = "/uapi/domestic-stock/v1/quotations/inquire-price"
    tr_id = "FHKST01010100"

    params = {
        "fid_cond_mrkt_div_code": market_code,
        "fid_input_iscd": stock_code
    }

    result = _api_request("GET", endpoint, tr_id, params=params)
    
    # output을 DataFrame으로 변환
    if 'output' in result:
        output = result['output']
        # 단일 딕셔너리를 리스트로 변환하여 DataFrame 생성
        df = pd.DataFrame([output])
        return df
    else:
        # output이 없는 경우 빈 DataFrame 반환
        return pd.DataFrame()


def get_daily_stock_data(stock_code: str, start_date: Optional[str] = None,
                         end_date: Optional[str] = None, period: Optional[str] = None,
                         market_code: str = "J"):
    """최근 데이터 조회 (최근 30일, 30주, 30월)"""
    # 날짜가 지정되지 않은 경우 최근 30일로 설정
    if start_date is None or end_date is None:
        today = datetime.now()
        if end_date is None:
            end_date = today.strftime("%Y%m%d")
        if start_date is None:
            start_date = (today - timedelta(days=30)).strftime("%Y%m%d")
    
    endpoint = "/uapi/domestic-stock/v1/quotations/inquire-daily-price"
    tr_id = "FHKST01010400"

    params = {
        "fid_cond_mrkt_div_code": market_code,
        "fid_input_iscd": stock_code,
        "fid_period_div_code": period if period else "D",  # D:일봉, W:주봉, M:월봉, Y:년봉
        "fid_org_adj_prc": "1"  # 수정주가 반영 여부 (1:수정주가, 0:원주가)
    }

    if start_date:
        params["strt_dt"] = start_date

    if end_date:
        params["end_dt"] = end_date

    return _api_request("GET", endpoint, tr_id, params=params)


def place_order(stock_code: str, order_type: str, quantity: int, price: int, order_division: str = "01"):
    """주식 주문"""
    endpoint = "/uapi/domestic-stock/v1/trading/order-cash"

    # 매수/매도에 따른 tr_id 설정
    if KIS_ENVIRONMENT == '실전투자':
        tr_id = "TTTC0802U" if order_type == "2" else "TTTC0801U"
    else:  # 모의투자
        tr_id = "VTTC0802U" if order_type == "2" else "VTTC0801U"

    # 주문 데이터
    order_data = {
        "CANO": str(ACCOUNT).strip(),  # 계좌번호 (문자열로 변환, 공백 제거)
        "ACNT_PRDT_CD": str(ACCOUNT_PROD).strip(),  # 계좌상품코드
        "PDNO": stock_code,
        "ORD_DVSN": order_division,
        "ORD_QTY": str(quantity),
        "ORD_UNPR": str(price),
        "SLL_BUY_DVSN_CD": order_type
    }

    # 해시키를 사용하여 POST 요청
    return _api_request("POST", endpoint, tr_id, data=order_data, use_hashkey=True)


def account_balance():
    """계좌 잔고 조회"""
    endpoint = "/uapi/domestic-stock/v1/trading/inquire-balance"

    # 환경에 따라 TR ID 설정
    if KIS_ENVIRONMENT == '실전투자':
        tr_id = "TTTC8434R"
    else:  # 모의투자
        tr_id = "VTTC8434R"

    params = {
        "CANO": str(ACCOUNT).strip(),  # 계좌번호
        "ACNT_PRDT_CD": str(ACCOUNT_PROD).strip(),  # 계좌상품코드
        "AFHR_FLPR_YN": "N",
        "OFL_YN": "N",
        "INQR_DVSN": "01",
        "UNPR_DVSN": "01",
        "FUND_STTL_ICLD_YN": "N",
        "FNCG_AMT_AUTO_RDPT_YN": "N",
        "PRCS_DVSN": "00",
        "CTX_AREA_FK100": "",
        "CTX_AREA_NK100": ""
    }
    return _api_request("GET", endpoint, tr_id, params=params)


def account_order_history(start_date: Optional[str] = None, end_date: Optional[str] = None):
    """계좌 주문 내역 조회"""
    endpoint = "/uapi/domestic-stock/v1/trading/inquire-daily-ccld"
    
    # 환경에 따라 TR ID 설정
    if KIS_ENVIRONMENT == '실전투자':
        tr_id = "TTTC8001R"
    else:  # 모의투자
        tr_id = "VTTC8001R"

    # 날짜가 지정되지 않은 경우 최근 7일로 설정
    if start_date is None or end_date is None:
        today = datetime.now()
        if end_date is None:
            end_date = today.strftime("%Y%m%d")
        if start_date is None:
            start_date = (today - timedelta(days=7)).strftime("%Y%m%d")

    params = {
        "CANO": str(ACCOUNT).strip(),  # 계좌번호
        "ACNT_PRDT_CD": str(ACCOUNT_PROD).strip(),  # 계좌상품코드
        "INQR_STRT_DT": start_date,
        "INQR_END_DT": end_date,
        "SLL_BUY_DVSN_CD": "00",
        "INQR_DVSN": "00",
        "PDNO": "",
        "CCLD_DVSN": "00",
        "ORD_GNO_BRNO": "",
        "ODNO": "",
        "INQR_DVSN_3": "00",
        "INQR_DVSN_1": "",
        "CTX_AREA_FK100": "",
        "CTX_AREA_NK100": ""
    }

    return _api_request("GET", endpoint, tr_id, params=params)


def buyable_amount(stock_code: str, price: int):
    """종목별 매수 가능 수량 조회"""
    endpoint = "/uapi/domestic-stock/v1/trading/inquire-psbl-order"
    
    # 환경에 따라 TR ID 설정
    if KIS_ENVIRONMENT == '실전투자':
        tr_id = "TTTC8908R"
    else:  # 모의투자
        tr_id = "VTTC8908R"

    data = {
        "CANO": str(ACCOUNT).strip(),  # 계좌번호
        "ACNT_PRDT_CD": str(ACCOUNT_PROD).strip(),  # 계좌상품코드
        "PDNO": stock_code,
        "ORD_UNPR": str(price),
        "ORD_DVSN": "01",
        "CMA_EVLU_AMT_ICLD_YN": "N",
        "OVRS_ICLD_YN": "N"
    }

    # POST 요청이지만 조회성 API이므로 해시키 미사용
    return _api_request("POST", endpoint, tr_id, data=data, use_hashkey=False)
