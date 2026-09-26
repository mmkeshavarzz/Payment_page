import requests
from bs4 import BeautifulSoup
import json
import os
from datetime import timezone, timedelta
import jdatetime

DATA_FILE = 'data.json'

def fetch_usd_price():
    url = "https://api.tabdeal.org/r/plots/currency/prices"
    # هدرها برای اینکه سایت فکر کنه ما یک انسان واقعی با مرورگر هستیم!
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
        "Accept-Language": "fa-IR,fa;q=0.9,en-US;q=0.8,en;q=0.7"
    }
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        # گشتن دنبال تگ قیمت دلار تو سایت TGJU
        data = response.json()

        price_toman = float(data.get("USDT_IRT", {}).get("price", 0))
        if price_toman > 0:
            
            # تبدیل تومان به ریال تر و تمیز
            return int(price_toman * 10)
        return None
    except Exception as e:
        print(f"ارور در دریافت قیمت از صرافی تبدیل: {e}")
        return None


def main():
    new_price = fetch_usd_price()
    
    if new_price:
        # فایل data.json رو می‌خونیم که فقط قیمت رو عوض کنیم و دست به مبلغ دلاری شما نزنیم
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
        else:
            data = {"usd_amount": 25, "usd_to_irr_rate": 0}
            
        data['usd_to_irr_rate'] = new_price
        
        # ⏰ تنظیم افق زمانی تهران (اختلاف 3:30+ نسبت به UTC)
        tehran_timezone = timezone(timedelta(hours=3, minutes=30))
        now_in_tehran = jdatetime.datetime.now(tehran_timezone)
        
        # 📅 قالب‌بندی به تاریخ زیبای شمسی و ساعت تهران
        data['last_updated'] = now_in_tehran.strftime('%Y/%m/%d - %H:%M')
        
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
            
        print(f"تبریک! قیمت جدید پیدا شد: {new_price} ریال")
    else:
        print("متاسفانه عملیات یافتن قیمت شکست خورد.")

if __name__ == "__main__":
    main()
