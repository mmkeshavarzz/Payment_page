import urllib.request
import json
import re
import sys
import os

def fetch_url(url, headers):
    """یه تابع ترتمیز برای درخواست دادن به سایت"""
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            status = response.getcode()
            content = response.read().decode('utf-8')
            return status, content
    except Exception as e:
        return 500, str(e)

def extract_price_from_html(html):
    """
    گشتن تو کدهای HTML سایت TGJU برای پیدا کردن قیمت دلار
    سایت معمولاً قیمت رو تو تگ‌هایی با ساختار خاص می‌ذاره.
    """
    # الگوی اول: تگ‌های استانداردی که TGJU برای قیمت لحظه‌ای استفاده می‌کنه
    patterns = [
        # معمولاً قیمت رو تو این اتریبیوت می‌ذارن:
        r'data-col="info\.last_trade\.PDrCotVal"[^>]*>([\d,]+)',
        # اگه نبود، می‌گردیم دنبال هرکسی که کلاس text-left داره و توش عدد بزرگیه:
        r'<td[^>]*class="text-left"[^>]*>([\d,]+)</td>',
        # الگوی عمومی‌تر برای قیمت‌های ریالی تو صفحه
        r'<span[^>]*class="value"[^>]*>([\d,]+)</span>'
    ]
    
    for p in patterns:
        match = re.search(p, html)
        if match:
            # کاماها رو حذف می‌کنیم و تبدیل به عدد می‌کنیم
            price_str = match.group(1).replace(',', '')
            return int(price_str)
    return None

def main():
    # لینک دقیق صفحه‌ای که خودت دادی
    url = "https://www.tgju.org/profile/price_dollar_rl"
    
    # هدرها برای اینکه شبیه یه کاربر واقعی به نظر برسیم، نه ربات!
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'fa-IR,fa;q=0.9,en-US;q=0.8,en;q=0.7',
    }
    
    print(f"🕵️‍♂️ Fetching directly from {url}...")
    status, content = fetch_url(url, headers)
    
    print(f"📡 HTTP Status: {status}")
    
    # اگه سایت ارور 403 (کلودفلر) یا 503 بده:
    if status != 200:
        print(f"⚠️ وای! سایت ارور داد. کد ارور: {status}")
        print(f"📄 تیکه اول جواب سرور: {content[:500]}")
        sys.exit(1)
        
    print("🔍 Searching for the magical dollar price in the HTML...")
    price_rial = extract_price_from_html(content)
    
    if not price_rial:
        print("❌ ای بابا! نتونستم قیمت رو تو HTML پیدا کنم. احتمالاً سایت قالبش رو عوض کرده یا بهمون کپچا داده.")
        # چاپ کردن 1000 کاراکتر اول HTML برای اینکه تو لاگ گیت‌هاب ببینیم سایت چی بهمون داده
        safe_content = content.replace('\n', ' ')
        print(f"📄 HTML Snippet (first 1000 chars): {safe_content[:1000]}")
        sys.exit(1)
        
    # سایت TGJU قیمت رو به *ریال* میده (مثلا 600,000)، ما برای درک بهتر می‌کنیمش تومان
    price_toman = price_rial // 10
    print(f"✅ پیدا شد! قیمت فعلی دلار: {price_toman:,} تومان (معادل {price_rial:,} ریال)")
    
    # خب، قرار بود برای 25 دلار حساب کنیم
    usd_amount = 25
    total_toman = price_toman * usd_amount
    print(f"💰 هزینه $ {usd_amount} $ دلار میشه: $ {total_toman:,} $ تومان")
    
    # مسیر ذخیره فایل JSON (پوشه data و فایل rate.json که تو عکست بود)
    data_path = os.path.join('data', 'rate.json')
    os.makedirs(os.path.dirname(data_path), exist_ok=True)
    
    # دیتایی که قراره ذخیره بشه
    output_data = {
        "usd_to_toman": price_toman,
        "total_price_toman": total_toman
    }
    
    # ذخیره در فایل
    with open(data_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
        
    print("🎉 rate.json با موفقیت آپدیت شد! خسته نباشی دلاور!")

if __name__ == "__main__":
    main()
