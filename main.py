"""Polling loop + orchestration."""
from __future__ import annotations

import logging
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

import dart_api
import filter_rule
import store
import telegram_send

LOGGER = logging.getLogger("dart_alert")


def _configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


def _poll_once(api_key: str, bot_token: str, chat_id: str, lookback_days: int) -> None:
    rows = dart_api.list_recent(api_key, lookback_days=lookback_days)
    LOGGER.info("poll: fetched %d rows", len(rows))
    new_hits = 0
    for row in rows:
        rcept_no = row.get("rcept_no")
        if not rcept_no or store.is_sent(rcept_no):
            continue
        try:
            text = dart_api.fetch_detail(api_key, rcept_no)
        except Exception as exc:
            LOGGER.warning("fetch_detail failed for %s: %s", rcept_no, exc)
            continue
        matched = filter_rule.match(text)
        if matched:
            alert = telegram_send.format_alert(
                corp_name=row.get("corp_name", ""),
                report_nm=row.get("report_nm", ""),
                flr_nm=row.get("flr_nm", ""),
                matched=matched,
                rcept_no=rcept_no,
                rcept_dt=row.get("rcept_dt", ""),
            )
            try:
                telegram_send.send(bot_token, chat_id, alert)
            except Exception as exc:
                LOGGER.error("telegram send failed for %s: %s", rcept_no, exc)
                continue  # leave unmarked so it retries next cycle
            new_hits += 1
            LOGGER.info(
                "alert sent rcept_no=%s corp=%s matched=%s",
                rcept_no, row.get("corp_name"), matched,
            )
        store.mark_sent(rcept_no)
        time.sleep(dart_api.REQUEST_SLEEP_SEC)
    if new_hits:
        LOGGER.info("poll done: %d new alert(s)", new_hits)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    load_dotenv(dotenv_path=Path(__file__).with_name(".env"))
    _configure_logging()

    store.DEFAULT_DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    api_key = os.environ["DART_API_KEY"]
    bot_token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]
    poll_interval = int(os.environ.get("POLL_INTERVAL_SEC", "60"))
    lookback_days = int(os.environ.get("LOOKBACK_DAYS", "1"))

    store.init()

    if store.is_empty():
        LOGGER.info("first run: bootstrapping existing disclosures (no send)")
        existing = dart_api.list_recent(api_key, lookback_days=lookback_days)
        ids = [r["rcept_no"] for r in existing if r.get("rcept_no")]
        inserted = store.mark_bulk(ids)
        LOGGER.info("bootstrap marked %d rcept_no (skipped)", inserted)

    run_once = os.environ.get("RUN_ONCE", "").lower() in ("1", "true", "yes")
    if run_once:
        LOGGER.info("one-shot mode (RUN_ONCE=1)")
        _poll_once(api_key, bot_token, chat_id, lookback_days)
        return

    LOGGER.info(
        "starting polling loop (interval=%ds lookback=%dd)",
        poll_interval, lookback_days,
    )
    while True:
        try:
            _poll_once(api_key, bot_token, chat_id, lookback_days)
        except Exception:
            LOGGER.exception("poll error")
        time.sleep(poll_interval)


if __name__ == "__main__":
    main()
