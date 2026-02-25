import pytest
import pandas as pd
import kis_utils as kis
from datetime import datetime, timedelta

def test_issue_access_token():
    """접근 토큰 발급 테스트"""
    access_token = kis.issue_access_token()
    assert isinstance(access_token, str)
    assert len(access_token) > 0

def test_issue_hashkey():
    """해시키 발급 테스트"""
    sample_body = {"foo": "bar"}
    hashkey = kis.issue_hashkey(sample_body)
    assert isinstance(hashkey, str)
    assert len(hashkey) > 0

def test_get_stock_price():
    """현재가 조회 테스트"""
    stock_code = "005930"  # 삼성전자
    price_df = kis.get_stock_price(stock_code)
    assert not price_df.empty
    assert 'stck_prpr' in price_df.columns
    
    # 가격이 정수형으로 변환 가능한지 확인
    price = int(price_df['stck_prpr'].iloc[0])
    assert price > 0

def test_get_daily_stock_data():
    """일봉 데이터 조회 테스트"""
    stock_code = "005930"
    today = datetime.now()
    start_date = (today - timedelta(days=10)).strftime("%Y%m%d")
    end_date = today.strftime("%Y%m%d")
    data = kis.get_daily_stock_data(stock_code, start_date, end_date)
    assert data is not None
    assert isinstance(data, pd.DataFrame)
    assert not data.empty

def test_account_balance():
    """계좌 잔고 조회 테스트"""
    balance = kis.account_balance()
    assert "output2" in balance
    assert len(balance['output2']) > 0
    # 예수금 확인
    deposit = int(balance['output2'][0]['dnca_tot_amt'])
    assert deposit >= 0

def test_account_order_history():
    """주문 내역 조회 테스트"""
    today = datetime.now()
    start_date = (today - timedelta(days=7)).strftime("%Y%m%d")
    end_date = today.strftime("%Y%m%d")
    order_history = kis.account_order_history(start_date, end_date)
    assert "output1" in order_history or "output" in order_history

def test_buyable_amount():
    """매수 가능 수량 조회 테스트"""
    stock_code = "005930"
    price = 70000
    result = kis.buyable_amount(stock_code, price)
    assert "output" in result

@pytest.mark.skip(reason="실제 주문 발생 위험이 있으므로 수동으로만 실행하세요.")
def test_place_order():
    """주식 주문 테스트 (주의: 실제 주문이 발생할 수 있음)"""
    stock_code = "005930"
    order_type = "2"  # 매수
    quantity = 1
    price = 70000
    order_division = "01"
    result = kis.place_order(stock_code, order_type, quantity, price, order_division)
    assert result is not None
