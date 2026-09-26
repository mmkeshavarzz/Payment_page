import json
import re
import ssl
from datetime import datetime, timezone
from urllib.request import urlopen, Request
from pathlib import Path

# آدرس اصلی و آدرس پراکسی برای دور زدن نگهبان‌های کلودفلر!
URL_MAIN = "https://api.tgju.org/v1/widget/tmp?keys=usd"
URL_PROXY = "https://api.allorigins.win/raw?url=https://api.tgju.org/v1/widget/tmp?keys=usd"
OUT = Path("data/rate.json")

def fetch_text(url: str) -> str:
    # لباس مبدل برای ربات ما که شبیه یه مرورگر واقعی به نظر برسه
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9,fa;q=0.8",
        "Referer": "https://www.tgju.org/"
    }
    
    # غیرفعال کردن گیر دادن‌های الکی به گواهینامه SSL
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    req = Request(url, headers=headers)
    with urlopen(req, timeout=20, context=ctx) as resp:
        return resp.read().decode("utf-8", errors="ignore")

def parse_usd_irr(raw: str) -> int:
    m = re.search(r'"p"\s*:\s*"([0-9,]+)"', raw)
    if not m:
        raise ValueError("وای! قیمت دلار تو خروجی پیدا نشد. سایت یه چیزی غیر از عدد برگردونده.")
    return int(m.group(1).replace(",", ""))

def main():
    usd_irr = None
    source = "TGJU"

    # عملیات اول: از در اصلی وارد میشیم
    try:
        print("🕵️‍♂️ Fetching directly from TGJU...")
        raw = fetch_text(URL_MAIN)
        usd_irr = parse_usd_irr(raw)
    except Exception as e:
        print(f"⚠️ Direct connection failed: {e}")
        # عملیات دوم: از تونل مخفی وارد میشیم (Plan B)
        try:
            print("🚀 Direct failed! Trying via AllOrigins Proxy...")
            raw = fetch_text(URL_PROXY)
            usd_irr = parse_usd_irr(raw)
            source = "TGJU (via Proxy)"
        except Exception as e2:
            raise RuntimeError(f"❌ داداش متاسفانه هر دو روش برای گرفتن قیمت فیلد شدن: {e2}")

    # محض احتیاط بهش می‌گیم اگه پوشه data نبود، بسازتش
    OUT.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "usd_irr": usd_irr,
        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
        "source": source
    }

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"🎉 BINGO! Rate updated successfully: {usd_irr} IRR")

if __name__ == "__main__":
    main()
