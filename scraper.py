#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Payment_page rate scraper
- Fetches USD/IRR from TGJU API endpoint
- Writes stable JSON to data/rate.json:
  {
    "usd_irr": <int>,
    "updated_at": "YYYY-MM-DD HH:mm:ss +0330",
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

# ===== Config =====
OUTPUT_PATH = os.path.join("data", "rate.json")
SOURCE_NAME = "TGJU"

# Endpoint used in your previous setup:
TGJU_URL = "https://api.tgju.org/v1/widget/tmp?keys=price_dollar_rl"

# Tehran fixed offset (+03:30) – aligned with your front-end day logic
TEHRAN_TZ = timezone(timedelta(hours=3, minutes=30))


def log(msg: str) -> None:
    print(f"[scraper] {msg}", flush=True)


def now_tehran_str() -> str:
    return datetime.now(TEHRAN_TZ).strftime("%Y-%m-%d %H:%M:%S %z")


def ensure_parent_dir(path: str) -> None:
    parent = os.path.dirname(path)
    if parent and not os.path.exists(parent):
        os.makedirs(parent, exist_ok=True)


def parse_int_from_any(raw) -> int:
    """
    Converts strings like:
      "2,334,800", "2334800", "2.334.800", "2 334 800", "۲٬۳۳۴٬۸۰۰"
    to int(2334800)
    """
    if raw is None:
        raise ValueError("rate value is None")

    s = str(raw).strip()

    # Persian digits -> English digits
    fa_digits = "۰۱۲۳۴۵۶۷۸۹"
    en_digits = "0123456789"
    trans = str.maketrans("".join(fa_digits), "".join(en_digits))
    s = s.translate(trans)

    # keep only digits
    digits = re.sub(r"[^\d]", "", s)
    if not digits:
        raise ValueError(f"cannot parse integer from value: {raw!r}")

    value = int(digits)
    if value <= 0:
        raise ValueError(f"parsed non-positive rate: {value}")
    return value


def extract_usd_irr(payload: dict) -> int:
    """
    TGJU response formats may vary. We try multiple known paths.
    """

    # Most likely shape in tgju widget:
    # payload["current"]["price_dollar_rl"]["p"]  (or "pf")
    candidates = []

    # 1) Deep known keys
    try:
        cur = payload.get("current", {})
        usd_obj = cur.get("price_dollar_rl", {})
        for k in ("p", "pf", "price", "value"):
            if k in usd_obj:
                candidates.append(usd_obj[k])
    except Exception:
        pass

    # 2) Alternative flat-ish keys
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

    # 3) last resort: recursive scan for keys containing dollar/usd + price-ish values
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

    # Try parse in order
    for c in candidates:
        try:
            return parse_int_from_any(c)
        except Exception:
            continue

    raise ValueError("USD/IRR not found in TGJU payload")


def fetch_json(url: str, timeout: int = 20) -> dict:
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
    """
    Returns existing usd_irr if available, else None
    """
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
        "updated_at": now_tehran_str(),
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

    # Fallback behavior:
    # If we already have an old valid rate.json, keep it and fail gracefully with exit 0
    # so the site remains functional.
    if old_rate:
        log("fallback: keeping existing rate.json (no overwrite)")
        return 0

    # No existing data => fail pipeline (important for visibility)
    log("fatal: no previous valid rate.json found")
    return 1


if __name__ == "__main__":
    sys.exit(main())
