import os
import sys
from typing import Optional, Dict, Any

# 현재 디렉토리를 경로에 추가하여 kis_utils 임포트 가능하게 함
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))
import kis_utils

def price(stock_code: str, market_code: str = "J") -> Dict[str, Any]:
    """
    주식의 현재가 정보를 조회합니다.
    
    Args:
        stock_code: 종목코드 (예: '005930')
        market_code: 시장구분 (기본값 'J')
    """
    df = kis_utils.price(stock_code, market_code)
    if df.empty:
        return {"error": f"종목코드 {stock_code}의 정보를 찾을 수 없습니다."}
    return df.iloc[0].to_dict()

def balance() -> Dict[str, Any]:
    """
    계좌의 잔고 현황 및 보유 종목 리스트를 조회합니다.
    """
    return kis_utils.balance()

def daily(stock_code: str, start_date: Optional[str] = None, 
          end_date: Optional[str] = None, period: str = "D") -> Dict[str, Any]:
    """
    주식의 기간별 시세(일봉, 주봉 등) 데이터를 조회합니다.
    
    Args:
        stock_code: 종목코드
        start_date: 시작일 (YYYYMMDD 형식)
        end_date: 종료일 (YYYYMMDD 형식)
        period: 봉 구분 ('D':일, 'W':주, 'M':월, 'Y':년)
    """
    return kis_utils.daily(stock_code, start_date, end_date, period)

def buy(stock_code: str, quantity: int, price: int, order_division: str = "01") -> Dict[str, Any]:
    """
    주식을 매수 주문합니다.
    
    Args:
        stock_code: 종목코드
        quantity: 매수 수량
        price: 매수 가격 (시장가는 0)
        order_division: 주문 구분 ('01':지정가, '03':시장가)
    """
    return kis_utils.buy(stock_code, quantity, price, order_division)

def sell(stock_code: str, quantity: int, price: int, order_division: str = "01") -> Dict[str, Any]:
    """
    주식을 매도 주문합니다.
    
    Args:
        stock_code: 종목코드
        quantity: 매도 수량
        price: 매도 가격 (시장가는 0)
        order_division: 주문 구분 ('01':지정가, '03':시장가)
    """
    return kis_utils.sell(stock_code, quantity, price, order_division)

def order_history(start_date: Optional[str] = None, end_date: Optional[str] = None) -> Dict[str, Any]:
    """
    최근 주문 및 체결 내역을 조회합니다.
    
    Args:
        start_date: 시작일 (YYYYMMDD)
        end_date: 종료일 (YYYYMMDD)
    """
    return kis_utils.order_history(start_date, end_date)

def buyable(stock_code: str, price_val: int) -> Dict[str, Any]:
    """
    지정가 기준 매수 가능 수량을 조회합니다.
    
    Args:
        stock_code: 종목코드
        price_val: 매수 희망 가격
    """
    return kis_utils.buyable(stock_code, price_val)

def token() -> str:
    """
    API 접근 토큰을 발급/갱신합니다.
    """
    return kis_utils.token()

if __name__ == "__main__":
    # 간단한 테스트
    print(price("005930"))
