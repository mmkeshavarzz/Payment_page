import urllib.request
import json
import re
import sys
import os
from datetime import datetime, timezone

def fetch_url(url, headers):
    """درخواست به سایت با هدر و timeout"""
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            status = response.getcode()
            content = response.read().decode("utf-8", errors="ignore")
            return status, content
    except Exception as e:
        return 500, str(e)

def extract_price_from_html(html):
    """
    استخراج قیمت دلار از HTML سایت TGJU
    خروجی: قیمت به ریال
    """
    patterns = [
        r'data-col="info\.last_trade\.PDrCotVal"[^>]*>([\d,]+)',
        r'<td[^>]*class="text-left"[^>]*>([\d,]+)</td>',
        r'<span[^>]*class="value"[^>]*>([\d,]+)</span>'
    ]

    for pattern in patterns:
        match = re.search(pattern, html)
        if match:
            price_str = match.group(1).replace(",", "").strip()
            if price_str.isdigit():
                return int(price_str)
    return None

def calc_smart_final(rate_irr, usd_amount=25):
    """
    فرمول نهایی مطابق با index.html:
    Math.floor((rate * 25) / 10000) * 10000 + 900
    """
    exact = rate_irr * usd_amount
    return (exact // 10000) * 10000 + 900

def main():
    url = "https://www.tgju.org/profile/price_dollar_rl"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "fa-IR,fa;q=0.9,en-US;q=0.8,en;q=0.7",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache"
    }

    print(f"Fetching from: {url}")
    status, content = fetch_url(url, headers)
    print(f"HTTP Status: {status}")

    if status != 200:
        print(f"ERROR: Site returned status {status}")
        print(content[:500])
        sys.exit(1)

    price_rial = extract_price_from_html(content)

    if not price_rial or price_rial <= 0:
        print("ERROR: Could not extract dollar price from HTML.")
        safe_content = content.replace("\n", " ")
        print(safe_content[:1000])
        sys.exit(1)

    final_amount = calc_smart_final(price_rial, 25)

    output_data = {
        "usd_irr": price_rial,
        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "source": "TGJU",
        "final_irr": final_amount
    }

    data_path = os.path.join("data", "rate.json")
    os.makedirs(os.path.dirname(data_path), exist_ok=True)

    with open(data_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    print("rate.json updated successfully")
    print(json.dumps(output_data, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
