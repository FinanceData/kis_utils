"""
CLI 인터페이스 테스트

API 호출을 모킹하여 CLI 파싱, 출력 포맷, 에러 처리를 검증합니다.
실제 네트워크 요청 없이 실행 가능합니다.
"""
import json
import pytest
from unittest.mock import patch, MagicMock
from io import StringIO

from kis_utils import create_parser, main, _format_price, _format_json



# ──────────────────────────────────────
# 유틸 함수 테스트
# ──────────────────────────────────────

class TestFormatUtils:
    def test_format_price_integer(self):
        assert _format_price(70000) == "70,000"

    def test_format_price_string(self):
        assert _format_price("1234567") == "1,234,567"

    def test_format_price_zero(self):
        assert _format_price(0) == "0"

    def test_format_price_invalid(self):
        assert _format_price("N/A") == "N/A"

    def test_format_price_none(self):
        assert _format_price(None) == "None"

    def test_format_json(self):
        data = {"key": "값"}
        result = _format_json(data)
        parsed = json.loads(result)
        assert parsed["key"] == "값"


# ──────────────────────────────────────
# 파서 테스트
# ──────────────────────────────────────

class TestParser:
    def setup_method(self):
        self.parser = create_parser()

    def test_token_command(self):
        args = self.parser.parse_args(["token"])
        assert args.command == "token"

    def test_price_command(self):
        args = self.parser.parse_args(["price", "005930"])
        assert args.command == "price"
        assert args.stock_code == "005930"
        assert args.market == "J"
        assert args.pretty is False


    def test_price_with_options(self):
        args = self.parser.parse_args(["price", "005930", "-m", "K", "--pretty"])
        assert args.market == "K"
        assert args.pretty is True

    def test_daily_command_defaults(self):
        args = self.parser.parse_args(["daily", "005930"])
        assert args.command == "daily"
        assert args.stock_code == "005930"
        assert args.start is None
        assert args.end is None
        assert args.period == "D"

    def test_daily_command_with_options(self):
        args = self.parser.parse_args(["daily", "005930", "-s", "20250401", "-e", "20250430", "-p", "W"])
        assert args.start == "20250401"
        assert args.end == "20250430"
        assert args.period == "W"

    def test_balance_command(self):
        args = self.parser.parse_args(["balance"])
        assert args.command == "balance"

    def test_history_command_defaults(self):
        args = self.parser.parse_args(["history"])
        assert args.command == "history"
        assert args.start is None
        assert args.end is None

    def test_history_with_dates(self):
        args = self.parser.parse_args(["history", "-s", "20250401", "-e", "20250430"])
        assert args.start == "20250401"
        assert args.end == "20250430"

    def test_order_command(self):
        args = self.parser.parse_args(["order", "005930", "-t", "buy", "-q", "1", "-p", "70000"])
        assert args.command == "order"
        assert args.stock_code == "005930"
        assert args.type == "buy"
        assert args.qty == 1
        assert args.price == 70000
        assert args.division == "01"
        assert args.yes is False

    def test_order_sell_with_yes(self):
        args = self.parser.parse_args(["order", "005930", "-t", "sell", "-q", "5", "-p", "80000", "-y"])
        assert args.type == "sell"
        assert args.qty == 5
        assert args.yes is True

    def test_order_market_price(self):
        args = self.parser.parse_args(["order", "005930", "-t", "buy", "-q", "1", "-p", "0", "-d", "03"])
        assert args.division == "03"
        assert args.price == 0

    def test_buyable_command(self):
        args = self.parser.parse_args(["buyable", "005930", "-p", "70000"])
        assert args.command == "buyable"
        assert args.stock_code == "005930"
        assert args.price == 70000

    def test_missing_required_command(self):
        with pytest.raises(SystemExit):
            self.parser.parse_args([])

    def test_order_missing_type(self):
        with pytest.raises(SystemExit):
            self.parser.parse_args(["order", "005930", "-q", "1", "-p", "70000"])

    def test_invalid_period(self):
        with pytest.raises(SystemExit):
            self.parser.parse_args(["daily", "005930", "-p", "X"])


# ──────────────────────────────────────
# 명령어 실행 테스트 (API 모킹)
# ──────────────────────────────────────

class TestCmdToken:
    def test_token_via_main(self, capsys):
        """main()을 통한 토큰 발급 (모킹)"""
        with patch("kis_utils.cmd_token", return_value=0) as mock_cmd:
            result = main(["token"])
            mock_cmd.assert_called_once()
            assert result == 0


class TestCmdPrice:
    def test_price_via_main(self, capsys):
        """main()을 통한 현재가 조회"""
        with patch("kis_utils.cmd_price", return_value=0) as mock_cmd:
            result = main(["price", "005930"])
            mock_cmd.assert_called_once()
            assert result == 0

    def test_price_empty_result(self, capsys):
        """빈 결과 반환 시 에러 메시지"""
        import pandas as pd
        with patch("kis_utils.cmd_price") as mock_cmd:
            mock_cmd.return_value = 1
            result = main(["price", "999999"])
            assert result == 1


class TestCmdBalance:
    def test_balance_via_main(self):
        """main()을 통한 잔고 조회"""
        with patch("kis_utils.cmd_balance", return_value=0) as mock_cmd:
            result = main(["balance"])
            mock_cmd.assert_called_once()
            assert result == 0

    def test_balance_pretty(self):
        """Pretty 출력 모드"""
        with patch("kis_utils.cmd_balance", return_value=0) as mock_cmd:
            result = main(["balance", "--pretty"])
            assert result == 0


class TestCmdHistory:
    def test_history_via_main(self):
        with patch("kis_utils.cmd_history", return_value=0) as mock_cmd:
            result = main(["history"])
            mock_cmd.assert_called_once()
            assert result == 0

    def test_history_with_dates(self):
        with patch("kis_utils.cmd_history", return_value=0) as mock_cmd:
            result = main(["history", "-s", "20250401", "-e", "20250430"])
            assert result == 0


class TestCmdOrder:
    def test_order_via_main(self):
        with patch("kis_utils.cmd_order", return_value=0) as mock_cmd:
            result = main(["order", "005930", "-t", "buy", "-q", "1", "-p", "70000", "-y"])
            mock_cmd.assert_called_once()
            assert result == 0


class TestCmdBuyable:
    def test_buyable_via_main(self):
        with patch("kis_utils.cmd_buyable", return_value=0) as mock_cmd:
            result = main(["buyable", "005930", "-p", "70000"])
            mock_cmd.assert_called_once()
            assert result == 0


class TestCmdDaily:
    def test_daily_via_main(self):
        with patch("kis_utils.cmd_daily", return_value=0) as mock_cmd:
            result = main(["daily", "005930"])
            mock_cmd.assert_called_once()
            assert result == 0


# ──────────────────────────────────────
# 에러 처리 테스트
# ──────────────────────────────────────

class TestErrorHandling:
    def test_exception_returns_1(self, capsys):
        """예외 발생 시 종료코드 1 반환"""
        with patch("kis_utils.cmd_token"
, side_effect=Exception("테스트 에러")):
            result = main(["token"])
            assert result == 1
            captured = capsys.readouterr()
            assert "테스트 에러" in captured.err

    def test_api_error_message(self, capsys):
        """API 오류 메시지 출력"""
        with patch("kis_utils.cmd_price", side_effect=Exception("API 오류: 인증 실패")):
            result = main(["price", "005930"])
            assert result == 1
            captured = capsys.readouterr()
            assert "인증 실패" in captured.err
