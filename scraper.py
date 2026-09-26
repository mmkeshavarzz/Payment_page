#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
import re
import sys
from datetime import datetime, timezone, timedeltadef now_tehran_iso():
    return datetime.now(TEHRAN_TZ).isoformat(🌟 مسیر طلایی که با بقیه هماهنگه
OUTPUT_PATH = os.path.join("data", "rate.json")
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
    candidates = []

    if isinstance(payload, list):
        payload_dict = {"items": payload}
    elif isinstance(payload, dict):
        payload_dict = payload
    else:
        payload_dict = {}

    # 1. ساختار رایج TGJU
    cur = payload_dict.get("current", {})
    if isinstance(cur, dict):
        usd = cur.get("price_dollar_rl", {})
        if isinstance(usd, dict):
            for k in ("p", "pf", "price", "value"):
                if k in usd:
                    candidates.append(usd[k])

    # 2. ساختارهای جایگزین
    paths = [
        ("price_dollar_rl", "p"),
        ("price_dollar_rl", "pf"),
        ("price_dollar_rl", "price"),
        ("price_dollar_rl",),
        ("usd_irr",),
        ("usd",),
        ("price",),
    ]
    for path in paths:
        obj = payload_dict
        ok = True
        for key in path:
            if isinstance(obj, dict) and key in obj:
                obj = obj[key]
            else:
                ok = False
                break
        if ok:
            candidates.append(obj)

    # 3. ساختار BRSAPI (لاستیک زاپاس)
    if "currency" in payload_dict and isinstance(payload_dict["currency"], list):
        for item in payload_dict["currency"]:
            if isinstance(item, dict) and item.get("name") == "دلار":
                candidates.append(item.get("price"))

    # 4. جستجوی عمیق و کارآگاهی
    def deep_search(data):
        if isinstance(data, dict):
            if "price_dollar_rl" in data:
                val = data["price_dollar_rl"]
                if isinstance(val, dict):
                    for k in ("p", "pf", "price", "value"):
                        if k in val:
                            candidates.append(val[k])
                else:
                    candidates.append(val)
            for v in data.values():
                deep_search(v)
        elif isinstance(data, list):
            for item in data:
                deep_search(item)

    deep_search(payload)

    for c in candidates:
        try:
            v = parse_int_from_any(c)
            if v > 100000:
                return v
        except Exception:
            pass

    raise ValueError("USD/IRR not found in payload")


def fetch_json(url, timeout=25):
    # 🌟 لباس مبدل مرورگر برای دور زدن بادیگاردهای کلودفلر
    req = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json,text/plain,*/*",
            "Referer": "https://tgju.org/"
        },
        method="GET",
    )
    with urlopen(req, timeout=timeout) as resp:
        charset = resp.headers.get_content_charset() or "utf-8"
        return json.loads(resp.read().decode(charset, errors="replace"))


def write_rate(path, usd_irr, source="TGJU"):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    data = {
        "usd_irr": int(usd_irr),
        "updated_at": now_tehran_iso(),
        "source": source
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def main():
    # لیست APIها (اولی افتاد تو جوب، میریم سراغ دومی!)
    apis = [
        {"url": "https://api.tgju.org/v1/widget/tmp?keys=price_dollar_rl", "source": "TGJU"},
        {"url": "https://brsapi.ir/FreeTsetmcBourseApi/Api_Free_Gold_Currency.json", "source": "BRSAPI"}
    ]

    for api in apis:
        try:
            payload = fetch_json(api["url"], timeout=20)
            usd_irr = extract_usd_irr(payload)
            write_rate(OUTPUT_PATH, usd_irr, source=api["source"])
            print(f"✅ Price updated successfully from {api['source']}:", OUTPUT_PATH)
            return 0
        except Exception as e:
            print(f"⚠️ Warning: Failed to fetch from {api['source']}. Error: {e}")
            continue

    print("❌ Error: All APIs completely failed! The bot is crying in the corner.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
