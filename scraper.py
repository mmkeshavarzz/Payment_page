#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
import re
import sys
from datetime import datetime, timezone, timedelta
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

OUTPUT_PATH = os.path.join("data", "rate.json")
TGJU_URL = "https://api.tgju.org/v1/widget/tmp?keys=price_dollar_rl"
TEHRAN_TZ = timezone(timedelta(hours=3, minutes=30))


def now_tehran_iso():
    return datetime.now(TEHRAN_TZ).isoformat(timespec="seconds")


def parse_int_from_any(raw):
    s = str(raw).strip()
    s = s.translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789"))
    digits = re.sub(r"[^\d]", "", s)
    if not digits:
        raise ValueError(f"cannot parse int from {raw!r}")
    v = int(digits)
    if v <= 0:
        raise ValueError(f"rate must be positive, got {v}")
    return v


def extract_usd_irr(payload):
    if not isinstance(payload, dict):
        raise ValueError("TGJU response is not a JSON object")

    candidates = []

    # ساختار فعلی API:
    # response.indicators[].name == "price_dollar_rl"
    response = payload.get("response", {})
    if isinstance(response, dict):
        indicators = response.get("indicators", [])
        if isinstance(indicators, list):
            for indicator in indicators:
                if not isinstance(indicator, dict):
                    continue
                if indicator.get("name") == "price_dollar_rl":
                    for key in ("p", "pf", "price", "value"):
                        if key in indicator:
                            candidates.append(indicator[key])

    # ساختارهای جایگزین TGJU
    current = payload.get("current", {})
    if isinstance(current, dict):
        usd = current.get("price_dollar_rl", {})
        if isinstance(usd, dict):
            for key in ("p", "pf", "price", "value"):
                if key in usd:
                    candidates.append(usd[key])

    paths = [
 candidates.append(usd[key])

    paths = [
        ("price_dollar_rl", "pf"),
        ("price_dollar_rl", "price"),
        ("price_dollar_rl",),
        ("usd_irr",),
        ("usd",),
        ("price",),
    ]

    for path in paths:
        obj = payload
        found = True
        for key in path:
            if isinstance(obj, dict) and key in obj:
                obj = obj[key]
            else:
                found = False
                break
        if found:
            candidates.append(obj)

    for candidate in candidates:
        try:
            return parse_int_from_any(candidate)
        except (TypeError, ValueError):
            continue

    raise ValueError("USD/IRR not found in TGJU response")


def fetch_json(url, timeout=25):
    req = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; PaymentPageBot/1.0)",
            "Accept": "application/json,text/plain,*/*",
        },
        method="GET",
    )
    with urlopen(req, timeout=timeout) as resp:
        charset = resp.headers.get_content_charset() or "utf-8"
        return json.loads(resp.read().decode(charset, errors="replace"))


def write_rate(path, usd_irr):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    data = {
        "usd_irr": int(usd_irr),
        "updated_at": now_tehran_iso(),
        "source": "TGJU",
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def main():
    try:
        payload = fetch_json(TGJU_URL, timeout=25)
        usd_irr = extract_usd_irr(payload)
        write_rate(OUTPUT_PATH, usd_irr)
        print("updated:", OUTPUT_PATH, "usd_irr:", usd_irr)
        return 0
    except (HTTPError, URLError, TimeoutError) as e:
        print("network error:", e)
        return 1
    except Exception as e:
        print("error:", e)
        return 1


if __name__ == "__main__":
    sys.exit(main())
