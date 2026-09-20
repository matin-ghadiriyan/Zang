# زنگ (Zang)

> پیام‌رسان تحت وب با قابلیت گفتگوی گروهی مبتنی بر **شناسه دسترسی** — ساخته‌شده با Flask و SQLAlchemy.

**زنگ** یک پیام‌رسان سبک، ماژولار و امن است که به کاربران اجازه می‌دهد بدون نیاز به افزودن دوستان، فقط با یک **شناسه** به گفتگوهای مشترک بپیوندند. هر گفتگو می‌تواند چند شناسه داشته باشد و هر کسی که یکی از آن شناسه‌ها را وارد کند، به همان گفتگو و پیام‌هایش دسترسی پیدا می‌کند.

---

## ✨ ویژگی‌ها

### مدیریت کاربران
- ثبت‌نام و ورود امن با هش رمز عبور (`werkzeug.security`)
- اعتبارسنجی نام کاربری، ایمیل و رمز عبور
- مدیریت نشست (Session) با دکوراتورهای `@is_logged_in` و `@is_guest`

### گفتگوهای مبتنی بر شناسه
- ساخت گفتگو با **یک یا چند شناسه دسترسی**
- پیوستن به گفتگو با وارد کردن شناسه — بدون نیاز به دعوت‌نامه
- چند کاربر می‌توانند گفتگوی مشترک داشته باشند
- کنترل دسترسی در سطح دیتابیس: هر پیام فقط برای اعضای همان گفتگو قابل مشاهده است
- تفکیک مالک گفتگو (`is_owner`) از اعضای عادی

### پیام‌رسانی
- ارسال، دریافت و حذف پیام
- نمایش **نام فرستنده** بالای هر پیام
- چینش هوشمند: پیام‌های خودت سمت راست، پیام‌های دیگران سمت چپ
- زمان‌بندی نمایش زمان ارسال
- محدودیت طول متن (حداکثر ۵۰۰۰ کاراکتر)

### زیرساخت و امنیت
- **Rate Limiting** بر اساس IP (پشتیبانی از `X-Forwarded-For`)
- صفحه‌های خطای اختصاصی (۴۰۱، ۴۰۳، ۴۰۴، ۴۲۹، ۵۰۰)
- **مهاجرت خودکار دیتابیس** هنگام بالا آمدن برنامه
- معماری مبتنی بر Blueprint برای توسعه‌پذیری
- تنظیمات از طریق متغیرهای محیطی (`.env`)

### رابط کاربری
- طراحی **راست‌به‌چپ (RTL)** و کاملاً فارسی
- تم تاریک با گرادیان بنفش/فیروزه‌ای
- فونت وزیرمتن
- واکنش‌گرا (Responsive) برای موبایل و دسکتاپ
- مودال‌های زیبا برای ساخت و پیوستن به گفتگو
- نوتیفیکیشن‌های Toast
- جست‌وجوی زنده در لیست گفتگوها

---

## 🧱 پشته فناوری

| لایه | فناوری |
|------|--------|
| زبان | Python 3.10+ |
| فریم‌ورک | Flask 3.x |
| ORM | SQLAlchemy (Flask-SQLAlchemy) |
| مهاجرت | Alembic / Flask-Migrate |
| دیتابیس | SQLite (پیش‌فرض) / قابل تغییر به MySQL یا PostgreSQL |
| فرم‌ها | Flask-WTF / WTForms |
| احراز هویت | Werkzeug Security + Session |
| محدودیت نرخ | Flask-Limiter + لیمیتِر داخلی |
| پاک‌سازی HTML | Bleach |
| فرانت‌اند | Jinja2 + Vanilla JS + CSS3 |
| فونت | Vazirmatn |
| سرور تولید | Gunicorn |
| تست | Pytest |

---

## 📁 ساختار پروژه

```text
zang/
├── app/
│   ├── __init__.py            # Application Factory + مهاجرت خودکار
│   ├── Access.py              # دکوراتورها و احراز هویت
│   ├── extensions.py          # نمونه‌های db و migrate
│   ├── models.py              # User, Chat, ChatMember, Message
│   ├── request_limiter.py     # محدودکننده نرخ درخواست
│   ├── routes/
│   │   ├── __init__.py        # ثبت Blueprintها
│   │   ├── home.py            # صفحه اصلی
│   │   ├── login_register.py  # ورود و ثبت‌نام
│   │   └── chatroom.py        # API گفتگوها و پیام‌ها
│   ├── static/
│   │   ├── css/style.css      # تم تاریک RTL
│   │   └── js/
│   │       ├── app.js         # ابزارهای عمومی (Toast, API, ...)
│   │       └── chat.js        # منطق چت
│   └── templats/              # قالب‌های Jinja2
│       ├── base.html
│       ├── index.html
│       ├── login_register/
│       ├── chatroom/
│       └── errors/
├── migrations/                # مهاجرت‌های Alembic
├── config.py                  # تنظیمات
├── run.py                     # نقطه ورود برنامه
├── requirements.txt
├── .env
└── README.md
```

> **نکته:** نام پوشه قالب‌ها `templats` (با یک «e») است و در `create_app()` به همین شکل تنظیم شده.

---

## 🗃️ مدل داده

```mermaid
 erDiagram
    User ||--o{ Chat : "owns"
    User ||--o{ ChatMember : "joins"
    User ||--o{ Message : "sends"
    Chat ||--o{ ChatMember : "has"
    Chat ||--o{ Message : "contains"

    User {
        int id PK
        string username UK
        string email UK
        string password
        datetime created_at
    }

    Chat {
        int id PK
        string title
        int user_id FK
        datetime created_at
        datetime updated_at
    }

    ChatMember {
        int id PK
        int chat_id FK
        int user_id FK
        string access_code
        bool is_owner
        datetime joined_at
    }

    Message {
        int id PK
        text content
        string role
        int chat_id FK
        int user_id FK
        datetime created_at
    }
```

---

## 🔌 API

همه اندپوینت‌ها به‌جز `/logout` نیازمند ورود هستند.

### گفتگوها

| متد | مسیر | توضیح |
|-----|------|-------|
| `GET` | `/chat/` | صفحه اصلی پیام‌رسان |
| `GET` | `/chat/api/chats` | لیست گفتگوهای کاربر |
| `POST` | `/chat/api/chats` | ساخت گفتگوی جدید با شناسه‌ها |
| `POST` | `/chat/api/chats/join` | پیوستن به گفتگو با شناسه |
| `GET` | `/chat/api/chats/<id>` | دریافت گفتگو همراه پیام‌ها |
| `PATCH` | `/chat/api/chats/<id>` | تغییر عنوان گفتگو |
| `DELETE` | `/chat/api/chats/<id>` | حذف گفتگو (فقط سازنده) |

### پیام‌ها

| متد | مسیر | توضیح |
|-----|------|-------|
| `POST` | `/chat/api/chats/<id>/messages` | ارسال پیام |
| `GET` | `/chat/api/chats/<id>/messages` | دریافت پیام‌های گفتگو |
| `DELETE` | `/chat/api/messages/<id>` | حذف پیام (فقط سازنده گفتگو) |

### نمونه درخواست — ساخت گفتگو

```json
POST /chat/api/chats
{
  "title": "تیم توسعه",
  "codes": ["team-dev", "ali", "sara"]
}
```

پاسخ:

```json
{
  "success": true,
  "chat": { "id": 4, "title": "تیم توسعه", "messages_count": 0, "members_count": 1 },
  "codes": ["team-dev", "ali", "sara"]
}
```

### نمونه درخواست — پیوستن با شناسه

```json
POST /chat/api/chats/join
{
  "code": "team-dev"
}
```

---

## 🚀 راه‌اندازی

### ۱. پیش‌نیاز

- Python 3.10 یا بالاتر

### ۲. دریافت کد

```bash
 git clone <repository-url>
cd zang
```

### ۳. ساخت محیط مجازی

**ویندوز:**

```bash
python -m venv venv
venv\Scripts\activate
```

**لینوکس / مک:**

```bash
python3 -m venv venv
source venv/bin/activate
```

### ۴. نصب وابستگی‌ها

```bash
pip install -r requirements.txt
```

### ۵. تنظیم متغیرهای محیطی

فایل `.env` را در ریشه پروژه بساز:

```env
SECRET_KEY=your-super-secret-key
DATABASE_URL=sqlite:///zang.db
DEBUG=1
PORT=5000
HOST=0.0.0.0
```

> برای MySQL:
> ```env
> DATABASE_URL=mysql+pymysql://user:password@localhost/zang
> ```

### ۶. اجرای برنامه

```bash
python run.py
```

برنامه روی [http://127.0.0.1:5000](http://127.0.0.1:5000) بالا می‌آید و **مهاجرت‌ها به‌صورت خودکار اعمال می‌شوند**.

---

## 🔄 مهاجرت دیتابیس

مهاجرت‌ها هنگام استارت برنامه به‌صورت خودکار اعمال می‌شوند (`_auto_update_database` در `app/__init__.py`).

اگر مدل‌ها را تغییر دادی:

```bash
python -m flask --app run:app db migrate -m "describe your changes"
python -m flask --app run:app db upgrade
```

برای بازگشت به نسخه قبلی:

```bash
python -m flask --app run:app db downgrade
```

---

## 🧪 تست

```bash
pytest
```

---

## 🔐 نکات امنیتی

- رمزهای عبور با الگوریتم امن هش می‌شوند.
- تمام ورودی‌های کاربر اعتبارسنجی و طول‌شان محدود می‌شود.
- دسترسی به هر گفتگو در سطح کوئری دیتابیس بررسی می‌شود (نه فقط در فرانت‌اند).
- محدودیت نرخ درخواست از حملات ساده DoS جلوگیری می‌کند.
- در محیط تولید `DEBUG=0` بگذار و از `gunicorn` استفاده کن.

---

## 🛣️ نقشه راه

- [ ] پیام‌های بلادرنگ با WebSocket
- [ ] بارگذاری فایل و تصویر
- [ ] اعلان‌ها
- [ ] حالت روشن / تاریک قابل انتخاب
- [ ] احراز هویت دو مرحله‌ای
- [ ] خروجی گرفتن از گفتگو

---

## 📄 مجوز

این پروژه در حال توسعه است و مجوز آن بعداً تعیین می‌شود.
