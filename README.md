<div dir="rtl" align="center">

# ⚡ AristaPanel ⚡

> **سیستم خودکار استخراج، اعتبارسنجی، دسته‌بندی و ترکیب کانفیگ‌های پروکسی از منابع عمومی تلگرام و گیت‌هاب**

[![Telegram](https://img.shields.io/badge/Telegram-229ED9?style=for-the-badge&logo=telegram&logoColor=white)](https://t.me/aristapanel)
[![YouTube](https://img.shields.io/badge/YouTube-FF0000?style=for-the-badge&logo=youtube&logoColor=white)](https://youtube.com/@aristaproject-m3o?si)
[![Element](https://img.shields.io/badge/Element-0DBD8B?style=for-the-badge&logo=element&logoColor=white)](https://matrix.to/#/%23aristaproject:matrix.org)
[![Web Panel](https://img.shields.io/badge/Web_Panel-F38020?style=for-the-badge&logo=cloudflare&logoColor=white)](https://arista-panel.arista-panel.workers.dev/)

---

## 🧩 معماری سیستم

| مؤلفه | توضیحات |
|-------|---------|
| **📡 telegram_extractor.py** | اسکرپ کانال‌های عمومی، استخراج محتوای متنی، شناسایی الگوهای پروکسی با regex، اعتبارسنجی ساختار هر کانفیگ |
| **🐙 github_extractor.py** | دریافت مستقیم فایل‌های خام از ۱۰ سورس مختلف، پشتیبانی از vmess://, vless://, trojan://, ss://, hysteria2://, tuic:// |
| **🔗 combine_configs.py** | ادغام خروجی دو استخراج‌کننده، حذف دایپلیکیت با MD5، تولید ساختار تیربندی با همپوشانی ۱۰ تایی |
| **⚙️ GitHub Actions** | زمانبندی `*/6 * * * *`، commit و push خودکار |

---

## 🚦 مدیریت کانال‌های مرده

| وضعیت | شرط | اقدام | مدت |
|--------|------|--------|------|
| تعلیق موقت | آخرین پست > ۴۸ ساعت | توقف اسکرپ | ۷ روز |
| کش مرده | ۳ بار متوالی فیلتر | توقف اسکرپ | ۲۴ ساعت |
| بلاک دائم | پس از ۷ روز تعلیق بدون فعالیت | حذف از چرخه | دائم |

**📂 فایل‌های وضعیت:** `configs/telegram/`

---

## 🔍 اعتبارسنجی کانفیگ‌ها

| پروتکل | بررسی‌ها |
|--------|---------|
| **vmess** | وجود فیلدهای `v, ps, add, port, id, aid` + اعتبار UUID + محدوده پورت |
| **vless / trojan** | وجود کاراکترهای `@` و `#` در رشته |
| **ss** | اعتبار base64 encoding + وجود `:` پس از دیکد |
| **سایر** | تطابق با الگوی پروتکل و عدم وجود کاراکترهای مخرب |

---

## 📢 کانال تلگرام

تمامی لینک‌های **سابسکریپشن**، **پروکسی‌های تلگرام (MTProto)**، **آیپی‌های تمیز کلادفلر** و کانفیگ‌های به‌روز روزانه در کانال تلگرام ارائه می‌شوند.

👉 [https://t.me/aristapanel](https://t.me/aristapanel)

---

## 🌐 پنل عمومی

برای **شخصی‌سازی خروجی**، **فیلتر بر اساس پروتکل**، **دریافت سابسکریپشن اختصاصی** از پنل عمومی استفاده کنید.

👉 [https://arista-panel.arista-panel.workers.dev/](https://arista-panel.arista-panel.workers.dev/)

---

## 📥 لینک‌های دسترسی به کانفیگ‌ها

<details>
<summary>📱 <b>V2rayNG • Hiddify • NekoBox • ...</b></summary>

<br/>

| منبع | ۵۰ | ۱۰۰ | ۱۵۰ | ۲۰۰ | ۲۵۰ | ۳۰۰ | ۴۰۰ | ۵۰۰ | ALL |
|:-----|:---:|:----:|:----:|:----:|:----:|:----:|:----:|:----:|:---:|
| **تلگرام** | [📥](https://cdn.jsdelivr.net/gh/aristapanell-cell/AriataPanel@main/configs/telegram/ALL/50.txt) | [📥](https://cdn.jsdelivr.net/gh/aristapanell-cell/AriataPanel@main/configs/telegram/ALL/100.txt) | [📥](https://cdn.jsdelivr.net/gh/aristapanell-cell/AriataPanel@main/configs/telegram/ALL/150.txt) | [📥](https://cdn.jsdelivr.net/gh/aristapanell-cell/AriataPanel@main/configs/telegram/ALL/200.txt) | [📥](https://cdn.jsdelivr.net/gh/aristapanell-cell/AriataPanel@main/configs/telegram/ALL/250.txt) | [📥](https://cdn.jsdelivr.net/gh/aristapanell-cell/AriataPanel@main/configs/telegram/ALL/300.txt) | [📥](https://cdn.jsdelivr.net/gh/aristapanell-cell/AriataPanel@main/configs/telegram/ALL/400.txt) | [📥](https://cdn.jsdelivr.net/gh/aristapanell-cell/AriataPanel@main/configs/telegram/ALL/500.txt) | [📥](https://cdn.jsdelivr.net/gh/aristapanell-cell/AriataPanel@main/configs/telegram/ALL/ALL.txt) |
| **گیت‌هاب** | [📥](https://cdn.jsdelivr.net/gh/aristapanell-cell/AriataPanel@main/configs/github/ALL/50.txt) | [📥](https://cdn.jsdelivr.net/gh/aristapanell-cell/AriataPanel@main/configs/github/ALL/100.txt) | [📥](https://cdn.jsdelivr.net/gh/aristapanell-cell/AriataPanel@main/configs/github/ALL/150.txt) | [📥](https://cdn.jsdelivr.net/gh/aristapanell-cell/AriataPanel@main/configs/github/ALL/200.txt) | [📥](https://cdn.jsdelivr.net/gh/aristapanell-cell/AriataPanel@main/configs/github/ALL/250.txt) | [📥](https://cdn.jsdelivr.net/gh/aristapanell-cell/AriataPanel@main/configs/github/ALL/300.txt) | [📥](https://cdn.jsdelivr.net/gh/aristapanell-cell/AriataPanel@main/configs/github/ALL/400.txt) | [📥](https://cdn.jsdelivr.net/gh/aristapanell-cell/AriataPanel@main/configs/github/ALL/500.txt) | [📥](https://cdn.jsdelivr.net/gh/aristapanell-cell/AriataPanel@main/configs/github/ALL/ALL.txt) |
| **ترکیبی** | [📥](https://cdn.jsdelivr.net/gh/aristapanell-cell/AriataPanel@main/configs/combined/ALL/50.txt) | [📥](https://cdn.jsdelivr.net/gh/aristapanell-cell/AriataPanel@main/configs/combined/ALL/100.txt) | [📥](https://cdn.jsdelivr.net/gh/aristapanell-cell/AriataPanel@main/configs/combined/ALL/150.txt) | [📥](https://cdn.jsdelivr.net/gh/aristapanell-cell/AriataPanel@main/configs/combined/ALL/200.txt) | [📥](https://cdn.jsdelivr.net/gh/aristapanell-cell/AriataPanel@main/configs/combined/ALL/250.txt) | [📥](https://cdn.jsdelivr.net/gh/aristapanell-cell/AriataPanel@main/configs/combined/ALL/300.txt) | [📥](https://cdn.jsdelivr.net/gh/aristapanell-cell/AriataPanel@main/configs/combined/ALL/400.txt) | [📥](https://cdn.jsdelivr.net/gh/aristapanell-cell/AriataPanel@main/configs/combined/ALL/500.txt) | [📥](https://cdn.jsdelivr.net/gh/aristapanell-cell/AriataPanel@main/configs/combined/ALL/ALL.txt) |

</details>

<details>
<summary>🔷 <b>SingBox</b></summary>

<br/>

| منبع | ۵۰ | ۱۰۰ | ۱۵۰ | ۲۰۰ | ۲۵۰ | ۳۰۰ | ۴۰۰ | ۵۰۰ | ALL |
|:-----|:---:|:----:|:----:|:----:|:----:|:----:|:----:|:----:|:---:|
| **تلگرام** | [📥](https://cdn.jsdelivr.net/gh/aristapanell-cell/AriataPanel@main/config.json/telegram/ALL/50.json) | [📥](https://cdn.jsdelivr.net/gh/aristapanell-cell/AriataPanel@main/config.json/telegram/ALL/100.json) | [📥](https://cdn.jsdelivr.net/gh/aristapanell-cell/AriataPanel@main/config.json/telegram/ALL/150.json) | [📥](https://cdn.jsdelivr.net/gh/aristapanell-cell/AriataPanel@main/config.json/telegram/ALL/200.json) | [📥](https://cdn.jsdelivr.net/gh/aristapanell-cell/AriataPanel@main/config.json/telegram/ALL/250.json) | [📥](https://cdn.jsdelivr.net/gh/aristapanell-cell/AriataPanel@main/config.json/telegram/ALL/300.json) | [📥](https://cdn.jsdelivr.net/gh/aristapanell-cell/AriataPanel@main/config.json/telegram/ALL/400.json) | [📥](https://cdn.jsdelivr.net/gh/aristapanell-cell/AriataPanel@main/config.json/telegram/ALL/500.json) | [📥](https://cdn.jsdelivr.net/gh/aristapanell-cell/AriataPanel@main/config.json/telegram/ALL/ALL.json) |
| **گیت‌هاب** | [📥](https://cdn.jsdelivr.net/gh/aristapanell-cell/AriataPanel@main/config.json/github/ALL/50.json) | [📥](https://cdn.jsdelivr.net/gh/aristapanell-cell/AriataPanel@main/config.json/github/ALL/100.json) | [📥](https://cdn.jsdelivr.net/gh/aristapanell-cell/AriataPanel@main/config.json/github/ALL/150.json) | [📥](https://cdn.jsdelivr.net/gh/aristapanell-cell/AriataPanel@main/config.json/github/ALL/200.json) | [📥](https://cdn.jsdelivr.net/gh/aristapanell-cell/AriataPanel@main/config.json/github/ALL/250.json) | [📥](https://cdn.jsdelivr.net/gh/aristapanell-cell/AriataPanel@main/config.json/github/ALL/300.json) | [📥](https://cdn.jsdelivr.net/gh/aristapanell-cell/AriataPanel@main/config.json/github/ALL/400.json) | [📥](https://cdn.jsdelivr.net/gh/aristapanell-cell/AriataPanel@main/config.json/github/ALL/500.json) | [📥](https://cdn.jsdelivr.net/gh/aristapanell-cell/AriataPanel@main/config.json/github/ALL/ALL.json) |
| **ترکیبی** | [📥](https://cdn.jsdelivr.net/gh/aristapanell-cell/AriataPanel@main/config.json/combined/ALL/50.json) | [📥](https://cdn.jsdelivr.net/gh/aristapanell-cell/AriataPanel@main/config.json/combined/ALL/100.json) | [📥](https://cdn.jsdelivr.net/gh/aristapanell-cell/AriataPanel@main/config.json/combined/ALL/150.json) | [📥](https://cdn.jsdelivr.net/gh/aristapanell-cell/AriataPanel@main/config.json/combined/ALL/200.json) | [📥](https://cdn.jsdelivr.net/gh/aristapanell-cell/AriataPanel@main/config.json/combined/ALL/250.json) | [📥](https://cdn.jsdelivr.net/gh/aristapanell-cell/AriataPanel@main/config.json/combined/ALL/300.json) | [📥](https://cdn.jsdelivr.net/gh/aristapanell-cell/AriataPanel@main/config.json/combined/ALL/400.json) | [📥](https://cdn.jsdelivr.net/gh/aristapanell-cell/AriataPanel@main/config.json/combined/ALL/500.json) | [📥](https://cdn.jsdelivr.net/gh/aristapanell-cell/AriataPanel@main/config.json/combined/ALL/ALL.json) |

</details>

<details>
<summary>🔶 <b>ClashMeta</b></summary>

<br/>

| منبع | ۵۰ | ۱۰۰ | ۱۵۰ | ۲۰۰ | ۲۵۰ | ۳۰۰ | ۴۰۰ | ۵۰۰ | ALL |
|:-----|:---:|:----:|:----:|:----:|:----:|:----:|:----:|:----:|:---:|
| **تلگرام** | [📥](https://cdn.jsdelivr.net/gh/aristapanell-cell/AriataPanel@main/config.yaml/telegram/ALL/50.yaml) | [📥](https://cdn.jsdelivr.net/gh/aristapanell-cell/AriataPanel@main/config.yaml/telegram/ALL/100.yaml) | [📥](https://cdn.jsdelivr.net/gh/aristapanell-cell/AriataPanel@main/config.yaml/telegram/ALL/150.yaml) | [📥](https://cdn.jsdelivr.net/gh/aristapanell-cell/AriataPanel@main/config.yaml/telegram/ALL/200.yaml) | [📥](https://cdn.jsdelivr.net/gh/aristapanell-cell/AriataPanel@main/config.yaml/telegram/ALL/250.yaml) | [📥](https://cdn.jsdelivr.net/gh/aristapanell-cell/AriataPanel@main/config.yaml/telegram/ALL/300.yaml) | [📥](https://cdn.jsdelivr.net/gh/aristapanell-cell/AriataPanel@main/config.yaml/telegram/ALL/400.yaml) | [📥](https://cdn.jsdelivr.net/gh/aristapanell-cell/AriataPanel@main/config.yaml/telegram/ALL/500.yaml) | [📥](https://cdn.jsdelivr.net/gh/aristapanell-cell/AriataPanel@main/config.yaml/telegram/ALL/ALL.yaml) |
| **گیت‌هاب** | [📥](https://cdn.jsdelivr.net/gh/aristapanell-cell/AriataPanel@main/config.yaml/github/ALL/50.yaml) | [📥](https://cdn.jsdelivr.net/gh/aristapanell-cell/AriataPanel@main/config.yaml/github/ALL/100.yaml) | [📥](https://cdn.jsdelivr.net/gh/aristapanell-cell/AriataPanel@main/config.yaml/github/ALL/150.yaml) | [📥](https://cdn.jsdelivr.net/gh/aristapanell-cell/AriataPanel@main/config.yaml/github/ALL/200.yaml) | [📥](https://cdn.jsdelivr.net/gh/aristapanell-cell/AriataPanel@main/config.yaml/github/ALL/250.yaml) | [📥](https://cdn.jsdelivr.net/gh/aristapanell-cell/AriataPanel@main/config.yaml/github/ALL/300.yaml) | [📥](https://cdn.jsdelivr.net/gh/aristapanell-cell/AriataPanel@main/config.yaml/github/ALL/400.yaml) | [📥](https://cdn.jsdelivr.net/gh/aristapanell-cell/AriataPanel@main/config.yaml/github/ALL/500.yaml) | [📥](https://cdn.jsdelivr.net/gh/aristapanell-cell/AriataPanel@main/config.yaml/github/ALL/ALL.yaml) |
| **ترکیبی** | [📥](https://cdn.jsdelivr.net/gh/aristapanell-cell/AriataPanel@main/config.yaml/combined/ALL/50.yaml) | [📥](https://cdn.jsdelivr.net/gh/aristapanell-cell/AriataPanel@main/config.yaml/combined/ALL/100.yaml) | [📥](https://cdn.jsdelivr.net/gh/aristapanell-cell/AriataPanel@main/config.yaml/combined/ALL/150.yaml) | [📥](https://cdn.jsdelivr.net/gh/aristapanell-cell/AriataPanel@main/config.yaml/combined/ALL/200.yaml) | [📥](https://cdn.jsdelivr.net/gh/aristapanell-cell/AriataPanel@main/config.yaml/combined/ALL/250.yaml) | [📥](https://cdn.jsdelivr.net/gh/aristapanell-cell/AriataPanel@main/config.yaml/combined/ALL/300.yaml) | [📥](https://cdn.jsdelivr.net/gh/aristapanell-cell/AriataPanel@main/config.yaml/combined/ALL/400.yaml) | [📥](https://cdn.jsdelivr.net/gh/aristapanell-cell/AriataPanel@main/config.yaml/combined/ALL/500.yaml) | [📥](https://cdn.jsdelivr.net/gh/aristapanell-cell/AriataPanel@main/config.yaml/combined/ALL/ALL.yaml) |

</details>

---

## 🎯 آی‌پی‌های تست‌شده و بهینه

> ⚡ **کمترین latency • بیشترین پایداری • به‌روزرسانی خودکار**

| فایل | توضیحات | لینک |
|:-----|---------|:----:|
| `ip_only.txt` | فقط آی‌پی | [📥](https://github.com/newtest2354-commits/testGit/tree/main/best_ip/ip_only.txt) |
| `ip_port.txt` | آی‌پی و پورت | [📥](https://github.com/newtest2354-commits/testGit/tree/main/best_ip/ip_port.txt) |
| `ip_port_cdn_sni_country_type.txt` | اطلاعات کامل (CDN, SNI, کشور, نوع) | [📥](https://github.com/newtest2354-commits/testGit/tree/main/best_ip/ip_port_cdn_sni_country_type.txt) |
| **پوشه کامل** | همه فایل‌ها | [📁](https://github.com/newtest2354-commits/testGit/tree/main/best_ip) |

---

## 📱 کلاینت‌های پشتیبانی‌شده

| نام کلاینت | سیستم‌عامل | لینک دانلود |
|:-----------|:-----------|:-----------:|
| **V2rayNG** | Android | [📥](https://github.com/2dust/v2rayNG/releases) |
| **Hiddify** | Android • iOS • Windows • macOS • Linux | [📥](https://github.com/hiddify/hiddify-app/releases) |
| **NekoBox** | Android | [📥](https://github.com/MatsuriDayo/NekoBoxForAndroid/releases) |
| **SingBox** | Android • iOS • Windows • macOS • Linux | [📥](https://github.com/SagerNet/sing-box/releases) |
| **ClashMeta** | Android • iOS • Windows • macOS • Linux | [📥](https://github.com/MetaCubeX/Clash.Meta/releases) |
| **v2rayN** | Windows | [📥](https://github.com/2dust/v2rayN/releases) |
| **Nekoray** | Windows • macOS • Linux | [📥](https://github.com/MatsuriDayo/nekoray/releases) |
| **Streisand** | Windows • macOS • Linux | [📥](https://github.com/SagerNet/Streisand/releases) |
| **Shadowrocket** | iOS | [📥](https://apps.apple.com/app/shadowrocket/id932747118) |
| **FairVPN** | iOS • macOS | [📥](https://apps.apple.com/app/fairvpn/id1533888676) |
| **V2Box** | iOS | [📥](https://apps.apple.com/app/v2box-v2ray-client/id6446814690) |
| **FoXray** | iOS | [📥](https://apps.apple.com/app/foxray/id6448898396) |

---

❤️ ساخته شده توسط تیم آریستا (🇲‌🇲‌🇩‌) ❤️

</div>
