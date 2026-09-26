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
    candidates = []

    cur = payload.get("current", {})
    if isinstance(cur, dict):
      usd = cur.get("price_dollar_rl", {})
      if isinstance(usd, dict):
          for k in ("p", "pf", "price", "value"):
              if k in usd:
                  candidates.append(usd[k])

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

    for c in candidates:
        try:
            return parse_int_from_any(c)
        except Exception:
            pass

    raise ValueError("USD/IRR not found in payload")


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
        "source": "TGJU"
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def main():
    try:
        payload = fetch_json(TGJU_URL, timeout=25)
        usd_irr = extract_usd_irr(payload)
        write_rate(OUTPUT_PATH, usd_irr)
        print("updated:", OUTPUT_PATH)
        return 0
    except (HTTPError, URLError, TimeoutError) as e:
        print("network error:", e)
        return 1
    except Exception as e:
        print("error:", e)
        return 1


if __name__ == "__main__":
    sys.exit(main())
