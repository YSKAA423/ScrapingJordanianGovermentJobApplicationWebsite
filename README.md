# لوحة متابعة الوظائف الحكومية الأردنية

منصة تجمع إعلانات الوظائف من موقع applyjobs.spac.gov.jo بشكل تلقائي، وتعرضها في جدول قابل للبحث والتصفية، مع وضعين للعرض (فاتح/داكن) وتحديث مجدول مرتين يوميًا (حوالي 08:00 و 17:00 بتوقيت عمّان) عبر GitHub Actions.

## المتطلبات
- Python 3.10+ (مفضل داخل بيئة افتراضية `venv`)
- الحزم: requests, beautifulsoup4 (`pip install -r requirements.txt`)

## التشغيل محليًا
1) إنشاء وتفعيل البيئة الافتراضية (اختياري لكنه موصى به):
   ```
   python3 -m venv .venv
   source .venv/bin/activate
   ```
2) تثبيت الاعتمادات:
   ```
   pip install -r requirements.txt
   ```
3) تشغيل السكربت لاستخراج البيانات:
   ```
   python scrape.py --output data/jobs.json
   ```
4) تشغيل خادم محلي لعرض الواجهة:
   ```
   python -m http.server 8000
   ```
   ثم فتح المتصفح على `http://localhost:8000/`.

## التحديث المجدول (GitHub Actions)
- ملف العمل: `.github/workflows/scrape.yml`
- الجدول: مرتان يوميًا (05:00 و 14:00 UTC ≈ 08:00 و 17:00 بتوقيت عمّان).
- يقوم العمل بتشغيل السكربت، ثم يحدّث `data/jobs.json` ويُجري دفعًا آليًا إلى الفرع `main` (يتطلب صلاحية الكتابة المضبوطة في ملف العمل).

## النشر المجاني (GitHub Pages)
1) تفعيل GitHub Pages من إعدادات المستودع: Source = `Deploy from a branch`، Branch = `main`، Folder = `/`.
2) التأكد من أن GitHub Actions مفعّلة ولديها صلاحية `contents: write`.
3) بعد كل تشغيل مجدول أو دفع يدوي، سيخدم GitHub Pages آخر نسخة من `index.html` و`data/jobs.json` على عنوان Pages الخاص بالمستودع.

## التحكم في المظهر
- زر التبديل في أعلى الصفحة يغيّر بين الوضع الفاتح والداكن.
- التفضيل يُخزَّن في `localStorage`.

---

# Jordanian Government Jobs Dashboard

Auto-collects job postings from applyjobs.spac.gov.jo and displays them in a searchable, filterable table with light/dark modes. Data refresh is scheduled twice daily (~08:00 and ~17:00 Amman) via GitHub Actions.

## Requirements
- Python 3.10+ (venv recommended)
- Dependencies: requests, beautifulsoup4 (`pip install -r requirements.txt`)

## Run locally
1) Create/activate venv (optional):
   ```
   python3 -m venv .venv
   source .venv/bin/activate
   ```
2) Install deps:
   ```
   pip install -r requirements.txt
   ```
3) Scrape data:
   ```
   python scrape.py --output data/jobs.json
   ```
4) Serve UI:
   ```
   python -m http.server 8000
   ```
   Then open `http://localhost:8000/`.

## Scheduled refresh (GitHub Actions)
- Workflow: `.github/workflows/scrape.yml`
- Schedule: twice daily (05:00 & 14:00 UTC ≈ 08:00 & 17:00 Amman).
- It runs the scraper, updates `data/jobs.json`, and pushes to `main` (needs `contents: write` permission in the workflow).

## Free hosting (GitHub Pages)
1) Enable Pages: Source `Deploy from a branch`, Branch `main`, Folder `/`.
2) Allow GitHub Actions to push updates (`contents: write`).
3) Pages will serve `index.html` + `data/jobs.json` after each scheduled run or manual push.

## Appearance
- Theme toggle in the header switches light/dark; preference stored in `localStorage`.
