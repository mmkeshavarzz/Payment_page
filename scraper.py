import json
import re
from datetime import datetime, timezone
from urllib.request import urlopen, Request

URL = "https://api.tgju.org/v1/widget/tmp?keys=usd"
OUT = "data/rate.json"

def fetch_text(url: str) -> str:
    req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(req, timeout=20) as resp:
        return resp.read().decode("utf-8", errors="ignore")

def parse_usd_irr(raw: str) -> int:
    # دنبال فیلد p می‌گردیم: "p":"850,000"
    m = re.search(r'"p"\s*:\s*"([0-9,]+)"', raw)
    if not m:
        raise ValueError("USD price not found in response")
    return int(m.group(1).replace(",", ""))

def main():
    raw = fetch_text(URL)
    usd_irr = parse_usd_irr(raw)

    payload = {
        "usd_irr": usd_irr,
        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
        "source": "TGJU"
    }

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"Updated {OUT}: usd_irr={usd_irr}")

if __name__ == "__main__":
    main()
