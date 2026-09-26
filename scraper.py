#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Payment_page rate scraper
- Fetches USD/IRR from TGJU API endpoint
- Writes stable JSON to data/rate.json:
  {
    "usd_irr": <int>,
    "updated_at": "<ISO8601, e.g. 2026-09-26T20:30:00+03:30>",
    "source": "TGJU"
  }
- Safe/clean logs for GitHub Actions
"""

import json
import os
import re
import sys
from datetime import datetime, timezone, timedelta
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

OUTPUT_PATH = os.path.join("data", "rate.json")
SOURCE_NAME = "TGJU"
TGJU_URL = "https://api.tgju.org/v1/widget/tmp?keys=price_dollar_rl"
TEHRAN_TZ = timezone(timedelta(hours=3, minutes=30))


def log(msg: str) -> None:
    print(f"[scraper] {msg}", flush=True)


def now_tehran_iso() -> str:
    return datetime.now(TEHRAN_TZ).isoformat(timespec="seconds")


def ensure_parent_dir(path: str) -> None:
    parent = os.path.dirname(path)
    if parent and not os.path.exists(parent):
        os.makedirs(parent, exist_ok=True)


def parse_int_from_any(raw) -> int:
    if raw is None:
        raise ValueError("rate value is None")

    s = str(raw).strip()
    s = s.translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789"))
    digits = re.sub(r"[^\d]", "", s)
    if not digits:
        raise ValueError(f"cannot parse integer from value: {raw!r}")

    value = int(digits)
    if value <= 0:
        raise ValueError(f"parsed non-positive rate: {value}")
    return value


def extract_usd_irr(payload: dict) -> int:
    candidates = []

    try:
        cur = payload.get("current", {})
        usd_obj = cur.get("price_dollar_rl", {})
        for k in ("p", "pf", "price", "value"):
            if k in usd_obj:
                candidates.append(usd_obj[k])
    except Exception:
        pass

    for path in [
        ("price_dollar_rl", "p"),
        ("price_dollar_rl", "pf"),
        ("price_dollar_rl", "price"),
        ("price_dollar_rl",),
        ("usd_irr",),
        ("usd",),
        ("price",),
    ]:
        obj = payload
        ok = True
        for key in path:
            if isinstance(obj, dict) and key in obj:
                obj = obj[key]
            else:
                ok = False
                break
        if ok:
            candidates.append(obj)

    def walk(o):
        if isinstance(o, dict):
            for k, v in o.items():
                lk = str(k).lower()
                if ("dollar" in lk or "usd" in lk) and isinstance(v, (str, int, float)):
                    candidates.append(v)
                walk(v)
        elif isinstance(o, list):
            for item in o:
                walk(item)

    walk(payload)

    for c in candidates:
        try:
            return parse_int_from_any(c)
        except Exception:
            continue

    raise ValueError("USD/IRR not found in TGJU payload")


def fetch_json(url: str, timeout: int = 25) -> dict:
    req = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; PaymentPageBot/1.0; +https://github.com/)",
            "Accept": "application/json,text/plain,*/*",
        },
        method="GET",
    )
    with urlopen(req, timeout=timeout) as resp:
        charset = resp.headers.get_content_charset() or "utf-8"
        body = resp.read().decode(charset, errors="replace")
        return json.loads(body)


def load_existing_rate(path: str):
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            old = json.load(f)
        old_rate = int(old.get("usd_irr", 0))
        return old_rate if old_rate > 0 else None
    except Exception:
        return None


def write_rate(path: str, usd_irr: int, source: str = SOURCE_NAME) -> None:
    ensure_parent_dir(path)
    data = {
        "usd_irr": int(usd_irr),
        "updated_at": now_tehran_iso(),
        "source": source,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def main() -> int:
    log("starting...")
    old_rate = load_existing_rate(OUTPUT_PATH)
    if old_rate:
        log(f"existing rate.json usd_irr={old_rate}")

    try:
        payload = fetch_json(TGJU_URL, timeout=25)
        usd_irr = extract_usd_irr(payload)
        write_rate(OUTPUT_PATH, usd_irr, SOURCE_NAME)
        log(f"success: usd_irr={usd_irr} -> {OUTPUT_PATH}")
        return 0

    except (HTTPError, URLError, TimeoutError) as e:
        log(f"network error: {e!r}")
    except json.JSONDecodeError as e:
        log(f"json decode error: {e!r}")
    except Exception as e:
        log(f"unexpected error: {e!r}")

    if old_rate:
        log("fallback: keeping existing rate.json (no overwrite)")
        return 0

    log("fatal: no previous valid rate.json found")
    return 1


if __name__ == "__main__":
    sys.exit(main())
