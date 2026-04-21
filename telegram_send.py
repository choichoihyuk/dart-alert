"""Telegram sendMessage via requests (HTML parse_mode)."""
from __future__ import annotations

import html
import logging
from typing import Iterable

import requests

LOGGER = logging.getLogger(__name__)

API_URL_TEMPLATE = "https://api.telegram.org/bot{token}/sendMessage"
VIEWER_URL_TEMPLATE = "https://dart.fss.or.kr/dsaf001/main.do?rcpNo={rcept_no}"
HTTP_TIMEOUT_SEC = 10


def send(bot_token: str, chat_id: str, text: str) -> None:
    url = API_URL_TEMPLATE.format(token=bot_token)
    resp = requests.post(
        url,
        data={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": "true",
        },
        timeout=HTTP_TIMEOUT_SEC,
    )
    try:
        resp.raise_for_status()
    except requests.HTTPError:
        LOGGER.error("telegram send failed: %s  body=%s", resp.status_code, resp.text[:200])
        raise
    data = resp.json()
    if not data.get("ok"):
        raise RuntimeError(f"telegram error: {data}")


def _format_date(yyyymmdd: str) -> str:
    if len(yyyymmdd) == 8 and yyyymmdd.isdigit():
        return f"{yyyymmdd[:4]}-{yyyymmdd[4:6]}-{yyyymmdd[6:]}"
    return yyyymmdd


def format_alert(
    *,
    corp_name: str,
    report_nm: str,
    flr_nm: str,
    matched: Iterable[str],
    rcept_no: str,
    rcept_dt: str,
) -> str:
    viewer_url = VIEWER_URL_TEMPLATE.format(rcept_no=rcept_no)
    kw_text = " / ".join(matched)
    return (
        f"<b>[DART] {html.escape(corp_name)}</b>\n"
        f"매칭: <b>{html.escape(kw_text)}</b>\n"
        f"보고자: {html.escape(flr_nm)}\n"
        f"공시일: {html.escape(_format_date(rcept_dt))}\n"
        f"보고서: {html.escape(report_nm)}\n"
        f'<a href="{html.escape(viewer_url, quote=True)}">공시뷰어 열기</a>'
    )


if __name__ == "__main__":
    msg = format_alert(
        corp_name="테스트<주식>&Co",
        report_nm="[기재정정]임원ㆍ주요주주특정증권등소유상황보고서",
        flr_nm="홍길동",
        matched=["장내매수", "증여"],
        rcept_no="20260420000535",
        rcept_dt="20260420",
    )
    assert "&lt;" in msg and "&amp;" in msg, "HTML escape must apply"
    assert "20260420000535" in msg and "장내매수 / 증여" in msg
    assert "2026-04-20" in msg, "date must be formatted"
    assert 'href="https://dart.fss.or.kr/dsaf001/main.do?rcpNo=20260420000535"' in msg
    print("telegram_send format_alert self-test OK")
    print("---")
    print(msg)
