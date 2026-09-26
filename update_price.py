import requests
from bs4 import BeautifulSoup
import json
import os
from datetime import timezone, timedelta
import jdatetime
import re


DATA_FILE = 'data.json'

def fetch_usd_price():
    url = "https://isignal.ir/gold-currency/usdollar/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "fa-IR,fa;q=0.9,en;q=0.8"
    }
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        # تبدیل اعداد فارسی احتمالی به انگلیسی برای جلوگیری از خطای عددی
        raw_html = response.text
        for fa_digit, en_digit in zip("۰۱۲۳۴۵۶۷۸۹", "0123456789"):
            raw_html = raw_html.replace(fa_digit, en_digit)
            
        soup = BeautifulSoup(raw_html, 'html.parser')
        text = soup.get_text()

        # شکار قیمت رسمی ثبت‌شده در متن صفحه (مثلاً: ۲,۳۴۰,۰۰۰ ریال)
        match = re.search(r'هر واحد دلار با قیمت\s*([\d,]+)\s*ریال', text)
        if not match:
            # الگوی جایگزین در صورت تغییرات نگارشی صفحه
            match = re.search(r'([\d,]{7,10})\s*ریال', text)

        if match:
            clean_price = match.group(1).replace(',', '').strip()
            return int(clean_price)
            
        return None
    except Exception as e:
        print(f"ارور در دریافت قیمت از سیگنال: {e}")
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

        data['source'] = 'سیگنال (Signal)'
        
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
            
        print(f"تبریک! قیمت جدید پیدا شد: {new_price} ریال")
    else:
        print("متاسفانه عملیات یافتن قیمت شکست خورد.")

if __name__ == "__main__":
    main()
