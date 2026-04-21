"""DART OpenAPI client: list.json + document.xml fetch."""
from __future__ import annotations

import io
import logging
import time
import zipfile
from datetime import datetime, timedelta, timezone
from typing import Any

import requests

LOGGER = logging.getLogger(__name__)

LIST_URL = "https://opendart.fss.or.kr/api/list.json"
DOCUMENT_URL = "https://opendart.fss.or.kr/api/document.xml"
# D001: 주식등의대량보유상황보고서 (5% 보고) — "(일반)"만 대상, "(약식)" 제외
# D002: 임원·주요주주특정증권등소유상황보고서
PBLNTF_DETAIL_TYPES = ("D001", "D002")
REPORT_NM_INCLUDES = {
    "D001": "(일반)",
}
REQUEST_SLEEP_SEC = 0.1
HTTP_TIMEOUT_SEC = 30
MAX_PAGES = 50  # safety guard for pagination loop
KST = timezone(timedelta(hours=9))


def list_recent(
    api_key: str,
    lookback_days: int = 1,
    page_count: int = 100,
) -> list[dict[str, Any]]:
    today = datetime.now(KST).date()
    bgn = (today - timedelta(days=lookback_days)).strftime("%Y%m%d")
    end = today.strftime("%Y%m%d")

    items: list[dict[str, Any]] = []
    for detail_ty in PBLNTF_DETAIL_TYPES:
        rows = _list_one(api_key, bgn, end, detail_ty, page_count)
        required = REPORT_NM_INCLUDES.get(detail_ty)
        if required:
            rows = [r for r in rows if required in r.get("report_nm", "")]
        items.extend(rows)
        time.sleep(REQUEST_SLEEP_SEC)
    return items


def _list_one(
    api_key: str, bgn: str, end: str, detail_ty: str, page_count: int
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    page_no = 1
    while page_no <= MAX_PAGES:
        params = {
            "crtfc_key": api_key,
            "bgn_de": bgn,
            "end_de": end,
            "pblntf_detail_ty": detail_ty,
            "page_no": str(page_no),
            "page_count": str(page_count),
        }
        resp = requests.get(LIST_URL, params=params, timeout=HTTP_TIMEOUT_SEC)
        resp.raise_for_status()
        data = resp.json()
        status = data.get("status")
        if status == "013":  # no data
            break
        if status != "000":
            raise RuntimeError(
                f"DART list.json error [{detail_ty}]: status={status} "
                f"message={data.get('message')}"
            )
        out.extend(data.get("list", []))
        total_page = int(data.get("total_page", 1))
        if page_no >= total_page:
            break
        page_no += 1
        time.sleep(REQUEST_SLEEP_SEC)
    else:
        LOGGER.warning(
            "list_recent hit MAX_PAGES=%d for %s, results may be truncated",
            MAX_PAGES, detail_ty,
        )
    return out


def fetch_detail(api_key: str, rcept_no: str) -> str:
    resp = requests.get(
        DOCUMENT_URL,
        params={"crtfc_key": api_key, "rcept_no": rcept_no},
        timeout=HTTP_TIMEOUT_SEC,
    )
    resp.raise_for_status()
    if resp.content[:2] != b"PK":
        raise RuntimeError(
            f"document.xml response is not a zip for rcept_no={rcept_no}: "
            f"{resp.text[:200]}"
        )
    with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
        chunks = [z.read(n) for n in z.namelist()]
    return b"".join(chunks).decode("utf-8", errors="ignore")


if __name__ == "__main__":
    import os
    import sys
    from dotenv import load_dotenv

    sys.stdout.reconfigure(encoding="utf-8")
    logging.basicConfig(level=logging.INFO)
    load_dotenv()
    key = os.environ["DART_API_KEY"]
    lookback = int(os.environ.get("LOOKBACK_DAYS", "1"))

    rows = list_recent(key, lookback_days=lookback)
    print(f"total: {len(rows)} (lookback_days={lookback})")
    for r in rows[:3]:
        print(
            f"  rcept_no={r.get('rcept_no')} | "
            f"corp={r.get('corp_name')} | "
            f"report={r.get('report_nm')}"
        )
