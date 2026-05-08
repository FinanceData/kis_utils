"""
한국투자증권 API 유틸리티 모듈 및 CLI 도구
"""
import argparse
import json
import logging
import os
import sys
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

import pandas as pd
import requests
from dotenv import load_dotenv, find_dotenv

# .env 파일 로드 및 경로 확인
env_path = find_dotenv()
if env_path:
    print(f"Loading .env from {env_path}")
    load_dotenv(env_path)
else:
    load_dotenv()

# 로깅 설정
logger = logging.getLogger(__name__)

# API BASE_URL 실전투자
KIS_BASE_URL = "https://openapi.koreainvestment.com:9443"
KIS_WS_URL = "ws://ops.koreainvestment.com:21000"

# API BASE_URL 모의투자
KIS_BASE_URL_VTS = "https://openapivts.koreainvestment.com:29443"
KIS_WS_URL_VTS = "ws://ops.koreainvestment.com:31000"

# .env 파일 로드
load_dotenv()

# 환경변수 읽기
KIS_ENVIRONMENT = os.getenv('KIS_ENVIRONMENT', '모의투자')

if KIS_ENVIRONMENT == '실전투자':
    APP_KEY = os.getenv('KIS_APP_KEY')
    APP_SECRET = os.getenv('KIS_APP_SECRET')
    ACCOUNT = os.getenv('KIS_ACCOUNT')
    ACCOUNT_PROD = os.getenv('KIS_ACCOUNT_PROD')
    BASE_URL = KIS_BASE_URL
    WS_URL = KIS_WS_URL
else:  # 모의투자
    APP_KEY = os.getenv('KIS_APP_KEY_VTS')
    APP_SECRET = os.getenv('KIS_APP_SECRET_VTS')
    ACCOUNT = os.getenv('KIS_ACCOUNT_VTS')
    ACCOUNT_PROD = os.getenv('KIS_ACCOUNT_PROD_VTS')
    BASE_URL = KIS_BASE_URL_VTS
    WS_URL = KIS_WS_URL_VTS

# 계좌 정보 검증 (CLI 실행이나 모듈 로드 시 체크)
def validate_config():
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

# 토큰 파일 경로
_TOKEN_FILE = os.path.join(os.path.expanduser("~"), ".access_token")

# 요청 횟수 제한 관리를 위한 변수
_request_count = 0

# ────────────────────────────────────────────────────────────────────────────────
# API 내부 함수
# ────────────────────────────────────────────────────────────────────────────────

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

def _refresh_token():
    """토큰 갱신"""
    url = f"{BASE_URL}/oauth2/tokenP"
    headers = {"Content-Type": "application/json"}
    body = {
        "grant_type": "client_credentials",
        "appkey": APP_KEY,
        "appsecret": APP_SECRET
    }
    response = requests.post(url, headers=headers, data=json.dumps(body))
    if response.status_code == 200:
        token_data = response.json()
        expires_at_str = token_data.get("access_token_token_expired")
        if expires_at_str:
            expiry_time = datetime.strptime(expires_at_str, "%Y-%m-%d %H:%M:%S")
        else:
            expires_in = token_data.get("expires_in", 86400)
            expiry_time = datetime.now() + timedelta(seconds=expires_in)
        _save_token_to_file(token_data, expiry_time)
    else:
        raise Exception(f"토큰 갱신 실패: {response.text}")

def _get_access_token() -> str:
    """유효한 토큰 반환, 필요시 갱신"""
    current_time = datetime.now()
    token_info = _load_token_from_file()
    if token_info:
        access_token = token_info.get("access_token")
        expires_at_str = token_info.get("expires_at")
        if access_token and expires_at_str:
            try:
                expiry_time = datetime.strptime(expires_at_str, "%Y-%m-%d %H:%M:%S")
                if current_time + timedelta(minutes=30) < expiry_time:
                    return access_token
            except ValueError:
                logger.warning("토큰 만료 시간 파싱 실패, 토큰 갱신")
    _refresh_token()
    token_info = _load_token_from_file()
    if token_info and token_info.get("access_token"):
        return token_info["access_token"]
    else:
        raise Exception("토큰 발급 및 저장 실패")

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
            return response.json()["HASH"]
        else:
            raise Exception(f"해시키 생성 실패: {response.text}")
    except Exception as e:
        raise Exception(f"해시키 생성 중 예외 발생: {str(e)}")

def _api_request(method: str, endpoint: str, tr_id: str, params: Optional[Dict] = None,
                data: Optional[Dict] = None, headers: Optional[Dict] = None, use_hashkey: bool = False):
    """API 요청 함수"""
    global _request_count
    access_token = _get_access_token()
    url = f"{BASE_URL}{endpoint}"
    default_headers = {
        "content-type": "application/json",
        "authorization": f"Bearer {access_token}",
        "appkey": APP_KEY,
        "appsecret": APP_SECRET,
        "tr_id": tr_id
    }
    if headers:
        default_headers.update(headers)
    if method.upper() == 'POST' and data and use_hashkey:
        default_headers["hashkey"] = _generate_hashkey(data)
    _request_count += 1
    try:
        if method.upper() == 'GET':
            response = requests.get(url, params=params, headers=default_headers)
        elif method.upper() == 'POST':
            response = requests.post(url, headers=default_headers, data=json.dumps(data))
        else:
            raise ValueError(f"지원하지 않는 HTTP 메소드: {method}")
        if response.status_code == 200:
            result = response.json()
            if result.get('rt_cd') == '0':
                return result
            else:
                raise Exception(f"API 오류 (RT_CD: {result.get('rt_cd')}): {result.get('msg1')}")
        else:
            raise Exception(f"HTTP 오류 (HTTP {response.status_code}): {response.text}")
    except requests.exceptions.RequestException as e:
        raise Exception(f"요청 예외 발생: {str(e)}")

# ────────────────────────────────────────────────────────────────────────────────
# 공개 API 함수
# ────────────────────────────────────────────────────────────────────────────────

def token() -> str:
    """접근토큰 신규 발급"""
    _refresh_token()
    token_info = _load_token_from_file()
    if token_info and token_info.get("access_token"):
        return token_info["access_token"]
    else:
        raise Exception("토큰 발급 실패")

def hashkey(request_body: Dict[str, Any]) -> str:
    """해시키 발급"""
    return _generate_hashkey(request_body)

def price(stock_code: str, market_code: str = "J"):
    """주식 현재가 조회 (DataFrame 반환)"""
    endpoint = "/uapi/domestic-stock/v1/quotations/inquire-price"
    tr_id = "FHKST01010100"
    params = {"fid_cond_mrkt_div_code": market_code, "fid_input_iscd": stock_code}
    result = _api_request("GET", endpoint, tr_id, params=params)
    if 'output' in result:
        return pd.DataFrame([result['output']])
    return pd.DataFrame()

def daily(stock_code: str, start_date: Optional[str] = None,
                         end_date: Optional[str] = None, period: Optional[str] = None,
                         market_code: str = "J"):
    """최근 데이터 조회"""
    if start_date is None or end_date is None:
        today = datetime.now()
        if end_date is None: end_date = today.strftime("%Y%m%d")
        if start_date is None: start_date = (today - timedelta(days=30)).strftime("%Y%m%d")
    endpoint = "/uapi/domestic-stock/v1/quotations/inquire-daily-price"
    tr_id = "FHKST01010400"
    params = {
        "fid_cond_mrkt_div_code": market_code,
        "fid_input_iscd": stock_code,
        "fid_period_div_code": period if period else "D",
        "fid_org_adj_prc": "1"
    }
    if start_date: params["strt_dt"] = start_date
    if end_date: params["end_dt"] = end_date
    return _api_request("GET", endpoint, tr_id, params=params)

def _place_order(stock_code: str, order_type: str, quantity: int, price: int, order_division: str = "01"):
    """주식 주문 내부 처리 (1: 매도, 2: 매수)"""
    validate_config()
    endpoint = "/uapi/domestic-stock/v1/trading/order-cash"
    
    # 매수/매도에 따른 TR ID 설정
    if KIS_ENVIRONMENT == '실전투자':
        tr_id = "TTTC0802U" if order_type == "2" else "TTTC0801U"
    else:  # 모의투자
        tr_id = "VTTC0802U" if order_type == "2" else "VTTC0801U"
        
    order_data = {
        "CANO": str(ACCOUNT).strip(),
        "ACNT_PRDT_CD": str(ACCOUNT_PROD).strip(),
        "PDNO": stock_code,
        "ORD_DVSN": order_division,
        "ORD_QTY": str(quantity),
        "ORD_UNPR": str(price),
        "SLL_BUY_DVSN_CD": order_type
    }
    return _api_request("POST", endpoint, tr_id, data=order_data, use_hashkey=True)

def buy(stock_code: str, quantity: int, price: int, order_division: str = "01"):
    """주식 매수 주문"""
    return _place_order(stock_code, "2", quantity, price, order_division)

def sell(stock_code: str, quantity: int, price: int, order_division: str = "01"):
    """주식 매도 주문"""
    return _place_order(stock_code, "1", quantity, price, order_division)

def balance():
    """계좌 잔고 조회"""
    validate_config()
    endpoint = "/uapi/domestic-stock/v1/trading/inquire-balance"
    tr_id = "TTTC8434R" if KIS_ENVIRONMENT == '실전투자' else "VTTC8434R"
    params = {
        "CANO": str(ACCOUNT).strip(),
        "ACNT_PRDT_CD": str(ACCOUNT_PROD).strip(),
        "AFHR_FLPR_YN": "N", "OFL_YN": "N", "INQR_DVSN": "01", "UNPR_DVSN": "01",
        "FUND_STTL_ICLD_YN": "N", "FNCG_AMT_AUTO_RDPT_YN": "N", "PRCS_DVSN": "00",
        "CTX_AREA_FK100": "", "CTX_AREA_NK100": ""
    }
    return _api_request("GET", endpoint, tr_id, params=params)

def order_history(start_date: Optional[str] = None, end_date: Optional[str] = None):
    """계좌 주문 내역 조회"""
    validate_config()
    endpoint = "/uapi/domestic-stock/v1/trading/inquire-daily-ccld"
    tr_id = "TTTC8001R" if KIS_ENVIRONMENT == '실전투자' else "VTTC8001R"
    if start_date is None or end_date is None:
        today = datetime.now()
        if end_date is None: end_date = today.strftime("%Y%m%d")
        if start_date is None: start_date = (today - timedelta(days=7)).strftime("%Y%m%d")
    params = {
        "CANO": str(ACCOUNT).strip(),
        "ACNT_PRDT_CD": str(ACCOUNT_PROD).strip(),
        "INQR_STRT_DT": start_date, "INQR_END_DT": end_date,
        "SLL_BUY_DVSN_CD": "00", "INQR_DVSN": "00", "PDNO": "", "CCLD_DVSN": "00",
        "ORD_GNO_BRNO": "", "ODNO": "", "INQR_DVSN_3": "00", "INQR_DVSN_1": "0",
        "CTX_AREA_FK100": "", "CTX_AREA_NK100": ""
    }
    return _api_request("GET", endpoint, tr_id, params=params)

def buyable(stock_code: str, price: int):
    """종목별 매수 가능 수량 조회"""
    validate_config()
    endpoint = "/uapi/domestic-stock/v1/trading/inquire-psbl-order"
    tr_id = "TTTC8908R" if KIS_ENVIRONMENT == '실전투자' else "VTTC8908R"
    params = {
        "CANO": str(ACCOUNT).strip(),
        "ACNT_PRDT_CD": str(ACCOUNT_PROD).strip(),
        "PDNO": stock_code, "ORD_UNPR": str(price), "ORD_DVSN": "01",
        "CMA_EVLU_AMT_ICLD_YN": "N", "OVRS_ICLD_YN": "N"
    }
    return _api_request("GET", endpoint, tr_id, params=params)

def unfilled():
    """계좌 미체결 내역 조회 (주문/체결 내역 API에서 미체결만 필터링)"""
    validate_config()
    # nccld API 대신 daily-ccld API의 미체결 옵션(02) 사용 (더 안정적)
    endpoint = "/uapi/domestic-stock/v1/trading/inquire-daily-ccld"
    tr_id = "TTTC8001R" if KIS_ENVIRONMENT == '실전투자' else "VTTC8001R"
    today = datetime.now().strftime("%Y%m%d")
    params = {
        "CANO": str(ACCOUNT).strip(),
        "ACNT_PRDT_CD": str(ACCOUNT_PROD).strip(),
        "INQR_STRT_DT": today, "INQR_END_DT": today,
        "SLL_BUY_DVSN_CD": "00", "INQR_DVSN": "00", "PDNO": "", "CCLD_DVSN": "02",
        "ORD_GNO_BRNO": "", "ODNO": "", "INQR_DVSN_3": "00", "INQR_DVSN_1": "0",
        "CTX_AREA_FK100": "", "CTX_AREA_NK100": ""
    }
    return _api_request("GET", endpoint, tr_id, params=params)

# ────────────────────────────────────────────────────────────────────────────────
# CLI 유틸리티
# ────────────────────────────────────────────────────────────────────────────────

def _format_json(data, indent=2):
    """JSON 데이터를 숫자형으로 변환을 시도한 후 포맷팅"""
    def _convert_numeric(obj):
        if isinstance(obj, dict):
            return {k: _convert_numeric(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [_convert_numeric(i) for i in obj]
        elif isinstance(obj, str):
            # 콤마 제거 후 숫자로 변환 시도
            clean_str = obj.replace(',', '').strip()
            if not clean_str: return obj
            try:
                if '.' in clean_str: return float(clean_str)
                return int(clean_str)
            except ValueError:
                return obj
        return obj

    converted_data = _convert_numeric(data)
    return json.dumps(converted_data, ensure_ascii=False, indent=indent)

def _format_price(value):
    try: return f"{int(value):,}"
    except: return str(value)

def cmd_token(args):
    token_val = token()
    print(f"접근 토큰 발급 완료")
    print(f"   토큰: {token_val[:20]}...{token_val[-10:]}")
    return 0

def cmd_price(args):
    # API 요청을 직접 수행하여 전체 응답을 가져옴
    endpoint = "/uapi/domestic-stock/v1/quotations/inquire-price"
    tr_id = "FHKST01010100"
    params = {"fid_cond_mrkt_div_code": args.market, "fid_input_iscd": args.stock_code}
    result = _api_request("GET", endpoint, tr_id, params=params)
    
    if args.pretty:
        if 'output' not in result:
            print(f"{args.stock_code} 시세 정보를 가져올 수 없습니다.")
            return 1
        row = result['output']
        fields = {
            "현재가": ("stck_prpr", True), "전일 대비": ("prdy_vrss", True),
            "등락률(%)": ("prdy_ctrt", False), "시가": ("stck_oprc", True),
            "고가": ("stck_hgpr", True), "저가": ("stck_lwpr", True),
            "거래량": ("acml_vol", True), "거래대금": ("acml_tr_pbmn", True),
        }
        print(f"[{args.stock_code}] 현재가 정보")
        print("-" * 36)
        for label, (col, is_price) in fields.items():
            if col in row:
                val = _format_price(row[col]) if is_price else row[col]
                print(f"  {label:>10}: {val}")
    else:
        print(_format_json(result))
    return 0

def cmd_daily(args):
    today = datetime.now()
    start = args.start or (today - timedelta(days=30)).strftime("%Y%m%d")
    end = args.end or today.strftime("%Y%m%d")
    result = daily(args.stock_code, start, end, args.period, args.market)
    
    if args.pretty:
        if "output" in result:
            items = result["output"]
            if isinstance(items, list) and len(items) > 0:
                df = pd.DataFrame(items)
                cols = ["stck_bsop_date", "stck_oprc", "stck_hgpr", "stck_lwpr", "stck_clpr", "acml_vol"]
                available = [c for c in cols if c in df.columns]
                if available:
                    display_df = df[available].copy()
                    display_df.columns = ["날짜", "시가", "고가", "저가", "종가", "거래량"][:len(available)]
                    print(f"[{args.stock_code}] 기간별 시세 ({start} ~ {end})")
                    print(display_df.to_string(index=False))
                else: print(_format_json(items))
            else: print("조회 결과가 없습니다.")
        else: print(_format_json(result))
    else:
        print(_format_json(result))
    return 0

def cmd_balance(args):
    result = balance()
    if args.pretty:
        if "output1" in result:
            stocks = result["output1"]
            if stocks:
                print("보유 종목")
                print("-" * 60)
                print(f"  {'종목명':>10}  {'보유수량':>8}  {'매입가':>12}  {'현재가':>12}  {'손익률':>8}")
                print("-" * 60)
                for s in stocks:
                    name, qty = s.get("prdt_name", ""), s.get("hldg_qty", "0")
                    buy_price = _format_price(s.get("pchs_avg_pric", "0").split(".")[0])
                    cur_price = _format_price(s.get("prpr", "0"))
                    pnl = s.get("evlu_pfls_rt", "0")
                    if int(qty) > 0: print(f"  {name:>10}  {qty:>8}  {buy_price:>12}  {cur_price:>12}  {pnl:>7}")
            else: print("보유 종목이 없습니다.")
        if "output2" in result and result["output2"]:
            summary = result["output2"][0]
            deposit = _format_price(summary.get("dnca_tot_amt", "0"))
            total_eval = _format_price(summary.get("tot_evlu_amt", "0"))
            print(f"\n  예수금 총액: {deposit}\n  총 평가금액: {total_eval}")
    else:
        print(_format_json(result))
    return 0

def cmd_history(args):
    today = datetime.now()
    start = args.start or (today - timedelta(days=7)).strftime("%Y%m%d")
    end = args.end or today.strftime("%Y%m%d")
    result = order_history(start, end)
    if args.pretty:
        if "output1" in result:
            orders = result["output1"]
            if orders:
                print(f"주문 내역 ({start} ~ {end})")
                print("-" * 70)
                for o in orders:
                    name = o.get("prdt_name", o.get("pdno", ""))
                    side = "매수" if o.get("sll_buy_dvsn_cd") == "02" else "매도"
                    qty = o.get("tot_ccld_qty", o.get("ord_qty", "0"))
                    price = _format_price(o.get("avg_prvs", o.get("ord_unpr", "0")))
                    status = o.get("ord_dvsn_name", "")
                    print(f"  {name} | {side} | {qty} | {price} | {status}")
            else: print("주문 내역이 없습니다.")
        else: print(_format_json(result))
    else:
        print(_format_json(result))
    return 0

def cmd_order(args):
    order_type = "2" if args.type == "buy" else "1"
    side_label = "매수" if args.type == "buy" else "매도"
    div_label = {"01": "지정가", "03": "시장가"}.get(args.division, args.division)
    if args.pretty and not args.yes:
        print(f"주문 확인\n   종목코드: {args.stock_code}\n   주문유형: {side_label} ({div_label})\n   수량: {args.qty}\n   가격: {_format_price(args.price)}")
        if input("\n진행하시겠습니까? (y/N): ").lower() != "y":
            print("주문이 취소되었습니다.")
            return 0
    
    # 분리된 함수 호출
    if order_type == "2":
        result = buy(args.stock_code, args.qty, args.price, args.division)
    else:
        result = sell(args.stock_code, args.qty, args.price, args.division)
        
    if args.pretty:
        print(f"{side_label} 주문 완료")
        if "output" in result:
            out = result["output"]
            print(f"   주문번호: {out.get('ODNO', 'N/A')}\n   주문시각: {out.get('ORD_TMD', 'N/A')}")
    else:
        print(_format_json(result))
    return 0

def cmd_unfilled(args):
    result = unfilled()
    if args.pretty:
        # daily-ccld API는 output1에 결과를 담아줌
        if "output1" in result:
            orders = result["output1"]
            if orders:
                print("미체결 내역 (당일)")
                print("-" * 75)
                print(f"  {'종목명':>12} | {'구분':>4} | {'미체결수량':>8} | {'주문가격':>10} | {'주문번호':>10}")
                print("-" * 75)
                for o in orders:
                    name = o.get("prdt_name", o.get("pdno", ""))
                    side = "매수" if o.get("sll_buy_dvsn_cd") == "02" else "매도"
                    # daily-ccld에서는 rmn_qty가 아닌 미체결수량 관련 필드 확인 필요 (보통 ord_qty - tot_ccld_qty)
                    ord_qty = int(o.get("ord_qty", "0"))
                    ccld_qty = int(o.get("tot_ccld_qty", "0"))
                    unfilled_qty = ord_qty - ccld_qty
                    price = _format_price(o.get("ord_unpr", "0"))
                    no = o.get("odno", "")
                    if unfilled_qty > 0:
                        print(f"  {name:>12} | {side:>4} | {unfilled_qty:>10} | {price:>12} | {no:>12}")
            else: print("미체결 내역이 없습니다.")
        else: print(_format_json(result))
    else:
        print(_format_json(result))
    return 0

def cmd_buyable(args):
    result = buyable(args.stock_code, args.price)
    if args.pretty:
        if "output" in result:
            out = result["output"]
            max_qty = out.get("nrcvb_buy_qty", out.get("ord_psbl_qty", "0"))
            print(f"[{args.stock_code}] 매수 가능 수량\n   가격 {_format_price(args.price)} 기준: 최대 {max_qty}")
    else:
        print(_format_json(result))
    return 0

def create_parser():
    parser = argparse.ArgumentParser(prog="kis_utils", description="한국투자증권 API CLI")
    # 공통 인자 추가를 위해 상위 파서 정의
    common_parser = argparse.ArgumentParser(add_help=False)
    common_parser.add_argument("--pretty", action="store_true", help="사람이 읽기 좋은 형식으로 출력")
    
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    subparsers.add_parser("token", parents=[common_parser]).set_defaults(func=cmd_token)
    
    p_price = subparsers.add_parser("price", parents=[common_parser])
    p_price.add_argument("stock_code")
    p_price.add_argument("-m", "--market", default="J")
    p_price.set_defaults(func=cmd_price)
    
    p_daily = subparsers.add_parser("daily", parents=[common_parser])
    p_daily.add_argument("stock_code")
    p_daily.add_argument("-s", "--start"); p_daily.add_argument("-e", "--end")
    p_daily.add_argument("-p", "--period", choices=["D", "W", "M", "Y"], default="D")
    p_daily.add_argument("-m", "--market", default="J")
    p_daily.set_defaults(func=cmd_daily)
    
    subparsers.add_parser("balance", parents=[common_parser]).set_defaults(func=cmd_balance)
    
    subparsers.add_parser("unfilled", parents=[common_parser]).set_defaults(func=cmd_unfilled)
    
    p_hist = subparsers.add_parser("history", parents=[common_parser])
    p_hist.add_argument("-s", "--start"); p_hist.add_argument("-e", "--end")
    p_hist.set_defaults(func=cmd_history)
    
    p_ord = subparsers.add_parser("order", parents=[common_parser])
    p_ord.add_argument("stock_code")
    p_ord.add_argument("-t", "--type", required=True, choices=["buy", "sell"])
    p_ord.add_argument("-q", "--qty", type=int, required=True)
    p_ord.add_argument("-p", "--price", type=int, required=True)
    p_ord.add_argument("-d", "--division", default="01")
    p_ord.add_argument("-y", "--yes", action="store_true")
    p_ord.set_defaults(func=cmd_order)
    
    p_buy = subparsers.add_parser("buyable", parents=[common_parser])
    p_buy.add_argument("stock_code")
    p_buy.add_argument("-p", "--price", type=int, required=True)
    p_buy.set_defaults(func=cmd_buyable)
    
    return parser

def main(argv=None):
    parser = create_parser()
    args = parser.parse_args(argv)
    try: return args.func(args)
    except Exception as e:
        print(f"오류 발생: {e}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())
