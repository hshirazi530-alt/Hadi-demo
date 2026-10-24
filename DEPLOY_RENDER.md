راهنمای گام‌به‌گام برای انتشار پروژه روی Render (نسخهٔ آزمایشی)

پیش‌نیازها
- حساب GitHub/GitLab/Bitbucket خصوصی یا یک مخزن خصوصی در سرویس مورد نظر
- حساب Render (https://render.com)
- دسترسی به کلیدهای محیطی و اطلاعات پایگاه داده (اگر نیاز است)
- در محیط محلی: Python 3.11+، virtualenv، pip

مسیر ساده در ویندوز (بدون Git در این محیط)
- Git و GitHub CLI در محیط آماده‌سازی نصب نیستند؛ بنابراین این پروژه از اینجا به GitHub push نشده است.
- فایل `3-Hadi-source-safe.zip` را از پوشهٔ بالادستی پروژه استخراج کنید، یا Git for Windows/GitHub Desktop را روی رایانهٔ خود نصب کنید.
- در GitHub Desktop وارد حساب خود شوید، گزینهٔ Add an Existing Repository را انتخاب و پوشهٔ استخراج‌شده را برگزینید؛ سپس Publish repository را بزنید و مخزن را Private نگه دارید.
- برای نمایش سایت، آدرس عمومی Render را با مشتری به اشتراک بگذارید؛ اگر لازم است مشتری سورس را هم ببیند، از GitHub به‌عنوان همکار دعوتش کنید. برای دمو لازم نیست مخزن عمومی شود.
- رمز عبور، توکن، کلید خصوصی یا مقدار `DJANGO_SECRET_KEY` را در چت یا فایل‌های پروژه وارد نکنید. ورود GitHub را فقط در برنامه/وب‌سایت رسمی انجام دهید.
- آرشیو قبلی `render-deploy-package.zip` و `pythonanywhere-deploy.zip` را آپلود نکنید؛ آرشیو اول ممکن است دیتابیس محلی داشته باشد. از بستهٔ `3-Hadi-source-safe.zip` که فایل‌های محلی از آن حذف شده‌اند استفاده کنید.

1) آماده‌سازی مخزن
- در پوشهٔ پروژه (ریشهٔ Ecomprj) یک مخزن Git محلی بسازید:
  git init
  git add .
  git commit -m "Initial project snapshot for render deployment\n\nCo-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"

- پوشه‌ها و فایل‌های حساس مانند db.sqlite3، media/، .env و .venv در .gitignore هستند؛ قبل از push مطمئن شوید مقادیری که نباید عمومی شوند حذف شده‌اند.

2) ساخت repo خصوصی و push
- در GitHub/GitLab یک repo خصوصی بسازید و remote آن را به مخزن محلی اضافه کنید:
  git remote add origin <repo-url>
  git branch -M main
  git push -u origin main
- پیش از commit/push، `git status --short` و `git diff --cached --name-only` را بررسی کنید. نباید فایل دیتابیس، `.env`، `media/`، `.venv/`، `staticfiles/` یا فایل کلید دیده شود.

3) پیکربندی Render
- وارد Render شوید و "New +" -> "Web Service" -> Connect via GitHub/GitLab انتخاب کنید.
- repo ای که ساخته‌اید را انتخاب کنید.
- گزینه runtime: Python، Branch: main.
- آدرس نهایی پیش‌نمایش: https://Hazhirmarket-demo.onrender.com/
- Build Command: pip install -r requirements.txt && python manage.py collectstatic --noinput
- Start Command: python manage.py migrate && python manage.py load_demo_data && gunicorn ecomprj.wsgi:application --bind 0.0.0.0:$PORT --workers 1 --threads 2
- Environment variables (Render -> Environment): حداقل‌های لازم:
  - DJANGO_DEBUG: False
  - DJANGO_SECRET_KEY: (Generate or paste a secure secret)
  - DJANGO_SECURE_SSL_REDIRECT: True
  - DJANGO_TRUST_X_FORWARDED_PROTO: True
  - DJANGO_DEMO_SERVE_MEDIA: True  # برای پیش‌نمایش demo — توجه: media در فایل‌سیستم ephemeral است
  - DJANGO_STRICT_STATIC_MANIFEST: False
  - DJANGO_SECURE_HSTS_SECONDS: 31536000  # HSTS برای HTTPS دائمی
  - DATABASE_URL: (اگر از Render PostgreSQL استفاده می‌کنید، از بخش Databases مقدار connectionString را بگیرید)

4) پایگاه داده
- برای دیتابیس demo می‌توانید از Render Managed Postgres (free) استفاده کنید. توجه: ترنسیشن free ممکن است محدودیت داشته باشد.

5) پس از اولین deploy
- اگر نیاز است فایل‌های استاتیک خاصی در manifest قرار ندارند، مطمئن شوید فایل manifest.webmanifest در static/ اضافه شده است.
- برای media موقت، DJANGO_DEMO_SERVE_MEDIA=True در محیط تنظیم شود؛ اما برای production از راه‌حل‌های ابری (S3 یا مشابه) استفاده کنید.

6) نکات امنیتی و محرمانه‌گی
- هرگز مقادیر حاوی API keys یا secret را به‌صورت عمومی push نکنید.
- از repo خصوصی استفاده کنید و فقط فایل‌های مورد نیاز را push کنید.

7) بروزرسانی و نشر مجدد
- تغییرات محلی را commit و push کنید؛ Render به‌طور خودکار build و redeploy می‌کند.

8) رفع خطاهای رایج
- خطای missing manifest.webmanifest: اطمینان از وجود فایل در static/ و اجرای collectstatic
- خطاهای جمع‌آوری استاتیک مرتبط با WhiteNoise: اگر manifest strict روشن است و فایل‌ها mismatch دارند، DJANGO_STRICT_STATIC_MANIFEST=False را تنظیم کنید یا فایل‌های لازم را اضافه کنید.

9) کار با media
- توجه: فایل‌های آپلود شده به filesystem render اغلب ephemeral هستند و پس از restart یا sleep پاک می‌شوند. برای ذخیره دائمی از S3، Backblaze B2 یا سرویس Object Storage پیشنهاد می‌شود.

اگر می‌خواهید، می‌توانم:
- یک آرشیو zip حاوی فایل‌های لازم برای push به repo خصوصی بسازم و به شما تحویل دهم (در حالتی که git روی این ماشین نصب نیست)
- یا، اگر دسترسی دارید، برای شما یک مخزن محلی git ایجاد و commit انجام دهم و راهنمای دقیق push به remote را بدهم.

پیشنهاد بعدی: آیا می‌خواهید که همین حالا یک مخزن محلی ایجاد و commit انجام شود (نیاز به git نصب‌شده دارد) یا به‌جای آن یک آرشیو zip آماده کنم؟
