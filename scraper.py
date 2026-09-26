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
TEHRAN_TZ = timezone(timedelta(hours=3, minutes=30HRAN_TZ = timezone(timedelta(hours=3, minutes=30_TZ).isoformat(timespec="seconds")


def parse_int_from_any(raw):
    text = str(raw).strip()
    text = text.translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789"))
    digits = re.sub(r"[^\d]", "", text)

    if not digits:
        raise ValueError(f"cannot parse int from {raw!r}")

    value = int(digits)

    if value <= 0:
        raise ValueError(f"rate must be positive, got {value}")

    return value


def extract_usd_irr(payload):
    if not isinstance(payload, dict):
        raise ValueError("TGJU response is not a JSON object")

    candidates = []

    # ساختار فعلی TGJU: response.indicators[].name == price_dollar_rl
    response = payload.get("response", {})

    if isinstance(response, dict):
        indicators = response.get("indicators", [])

        if isinstance(indicators, list):
            for indicator in indicators:
                if not isinstance(indicator, dict):
                    continue

                if indicator.get("name") != "price_dollar_rl":
                    continue

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
        ("price_dollar_rl", "p"),
        ("price_dollar_rl", "pf"),
        ("price_dollar_rl", "price"),
        ("price_dollar_rl", "value"),
        ("price_dollar_rl",),
        ("usd_irr",),
        ("usd",),
        ("price",),
    ]

    for path in paths:
        value = payload
        found = True

        for key in path:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                found = False
                break

        if found:
            candidates.append(value)

    for candidate in candidates:
        try:
            return parse_int_from_any(candidate)
        except (TypeError, ValueError):
            continue

    raise ValueError("USD/IRR not found in TGJU response")


def fetch_json(url, timeout=25):
    request = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; PaymentPageBot/1.0)",
            "Accept": "application/json,text/plain,*/*",
        },
        method="GET",
    )

    with urlopen(request, timeout=timeout) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        body = response.read().decode(charset, errors="replace")
        return json.loads(body)


def write_rate(path, usd_irr):
    directory = os.path.dirname(path)

    if directory:
        os.makedirs(directory, exist_ok=True)

    data = {
        "usd_irr": int(usd_irr),
        "updated_at": now_tehran_iso(),
        "source": "TGJU",
    }

    with open(path, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
        file.write("\n")


def main():
    try:
        payload = fetch_json(TGJU_URL, timeout=25)
        usd_irr = extract_usd_irr(payload)
        write_rate(OUTPUT_PATH, usd_irr)

        print("updated:", OUTPUT_PATH)
        print("usd_irr:", usd_irr)
        return 0

    except (HTTPError, URLError, TimeoutError) as error:
        print("network error:", error)
        return 1

    except Exception as error:
        print("error:", error)
        return 1


if __name__ == "__main__":
    sys.exit(main())
