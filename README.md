# VisualVerse 🎨

> **Matching Avatars & Banners Explorer** — تصفح وحمّل صور البروفايل والبنرات المتطابقة بجودة HD

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy)

---

## ✨ المميزات

- 🌙 **Dark Mode** عصري ومتجاوب مع جميع الأجهزة
- 🖼️ **شبكة كروت** تعرض Avatar 1 + Avatar 2 + Banner لكل ثنائي
- ⬇️ **تحميل HD** مباشر لكل صورة على حدة أو الكل دفعة واحدة
- 🔗 **نسخ الروابط** بنقرة واحدة
- 🎲 **ثنائي عشوائي** من أي تصنيف
- 🔍 **بحث فوري** + فلترة بالتصنيفات
- 📋 **قائمة / شبكة** — وضعا العرض
- 🔗 **مشاركة** برابط مباشر قابل للنسخ

## 📁 هيكل المشروع

```
VisualVerse/
├── server.js           # Express.js backend
├── package.json
├── render.yaml         # Render deployment config
├── .gitignore
├── README.md
├── data/
│   └── matching.json   # بيانات الثنائيات
└── public/
    └── index.html      # Frontend (HTML + Tailwind + JS)
```

## 🚀 تشغيل محلي

```bash
# تثبيت الاعتماديات
npm install

# تشغيل بوضع التطوير
npm run dev

# تشغيل في الإنتاج
npm start
```

سيعمل التطبيق على: **http://localhost:3000**

## 📡 API Endpoints

| Method | Endpoint | الوصف |
|--------|----------|-------|
| `GET` | `/api/pairs` | كل الثنائيات (مع فلاتر `?category=` و `?q=`) |
| `GET` | `/api/pairs/random` | ثنائي عشوائي |
| `GET` | `/api/pairs/:id` | ثنائي محدد |
| `GET` | `/api/categories` | قائمة التصنيفات مع العدد |
| `GET` | `/api/stats` | إحصائيات عامة |
| `POST` | `/api/pairs` | إضافة ثنائي جديد |
| `DELETE` | `/api/pairs/:id` | حذف ثنائي |

## ➕ إضافة ثنائيات جديدة

افتح [`data/matching.json`](data/matching.json) وأضف كائناً بهذا الشكل:

```json
{
  "id": "anime-005",
  "category": "anime",
  "title": "اسم الثنائي",
  "tags": ["وسم1", "وسم2"],
  "avatar1": {
    "label": "اسم الصورة 1",
    "url": "https://رابط-الصورة-المباشر.jpg"
  },
  "avatar2": {
    "label": "اسم الصورة 2",
    "url": "https://رابط-الصورة-المباشر.jpg"
  },
  "banner": {
    "label": "اسم البنر",
    "url": "https://رابط-البنر-المباشر.jpg"
  }
}
```

التصنيفات المتاحة: `anime` | `gaming` | `couples` | `aesthetic`

## ☁️ النشر على Render

1. ارفع المشروع على **GitHub**
2. اذهب إلى [render.com](https://render.com) → **New Web Service**
3. اربط المستودع
4. Render سيكتشف `render.yaml` تلقائياً
5. اضغط **Deploy** ✅

أو استخدم زر **Deploy to Render** أعلاه.

## 🛠️ التقنيات

- **Backend**: Node.js + Express.js
- **Frontend**: HTML5 + Tailwind CSS (CDN) + Vanilla JS
- **Storage**: JSON file (`data/matching.json`)
- **Hosting**: Render (Free tier)

---

صُنع بـ ❤️ — **VisualVerse** &copy; 2025
