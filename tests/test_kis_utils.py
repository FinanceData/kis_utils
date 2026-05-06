import pytest
import pandas as pd
import kis_utils as kis
from datetime import datetime, timedelta

def test_token():
    """접근 토큰 발급 테스트"""
    access_token = kis.token()
    assert isinstance(access_token, str)
    assert len(access_token) > 0

def test_hashkey():
    """해시키 발급 테스트"""
    sample_body = {"foo": "bar"}
    hashkey = kis.hashkey(sample_body)
    assert isinstance(hashkey, str)
    assert len(hashkey) > 0

def test_price():
    """현재가 조회 테스트"""
    stock_code = "005930"  # 삼성전자
    price_df = kis.price(stock_code)
    assert not price_df.empty
    assert 'stck_prpr' in price_df.columns
    
    # 가격이 정수형으로 변환 가능한지 확인
    price = int(price_df['stck_prpr'].iloc[0])
    assert price > 0

def test_daily():
    """일봉 데이터 조회 테스트"""
    stock_code = "005930"
    today = datetime.now()
    start_date = (today - timedelta(days=10)).strftime("%Y%m%d")
    end_date = today.strftime("%Y%m%d")
    result = kis.daily(stock_code, start_date, end_date)
    assert result is not None
    assert "output" in result

def test_balance():
    """계좌 잔고 조회 테스트"""
    balance = kis.balance()
    assert "output2" in balance
    assert len(balance['output2']) > 0
    # 예수금 확인
    deposit = int(balance['output2'][0]['dnca_tot_amt'])
    assert deposit >= 0

def test_order_history():
    """주문 내역 조회 테스트"""
    today = datetime.now()
    start_date = (today - timedelta(days=7)).strftime("%Y%m%d")
    end_date = today.strftime("%Y%m%d")
    order_history = kis.order_history(start_date, end_date)
    assert "output1" in order_history or "output" in order_history

def test_buyable():
    """매수 가능 수량 조회 테스트"""
    stock_code = "005930"
    price = 70000
    result = kis.buyable(stock_code, price)
    assert "output" in result

@pytest.mark.skip(reason="실제 주문 발생 위험이 있으므로 수동으로만 실행하세요.")
def test_buy_sell():
    """주식 매수/매도 주문 테스트"""
    stock_code = "005930"
    quantity = 1
    price = 70000
    
    # 매수 테스트
    buy_result = kis.buy(stock_code, quantity, price)
    assert buy_result is not None
    
    # 매도 테스트
    sell_result = kis.sell(stock_code, quantity, price)
    assert sell_result is not None
