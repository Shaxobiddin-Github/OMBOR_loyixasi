📦 OMBOR NAZORAT TIZIMI
Buyurtmachiga topshirish CHECKLIST
Loyiha nomi:

Ombor Nazorat — Local Warehouse Management System

Texnologiya:

Python (Django) + PostgreSQL + Face ID (offline) + QR Scanner

1️⃣ TIZIM ISHGA TUSHGANI TEKSHIRILDI

 Django server localda ishlayapti

 PostgreSQL server Windows service sifatida ishlayapti

 Kompyuter qayta yoqilganda tizim avtomatik ishga tushadi

 pgAdmin faqat texnik nazorat uchun (doim ochiq turishi shart emas)

2️⃣ MA’LUMOTLAR BAZASI (POSTGRESQL)

 PostgreSQL o‘rnatilgan (v18.x)

 Baza nomi: ombor_nazorat

 Django jadvallari yaratildi

 SQLite’dan PostgreSQL’ga ma’lumotlar ko‘chirildi

 Ma’lumotlar data directory da xavfsiz saqlanmoqda

 .db fayl yo‘q — bu PostgreSQL uchun normal holat

3️⃣ FOYDALANUVCHI ROLLARI

 Admin — to‘liq huquq

 Operator — kirim / chiqim

 Viewer — faqat ko‘rish

 Login / logout ishlaydi

 Ruxsatsiz amallar bloklangan

4️⃣ MAHSULOTLAR VA OMBOR

 Kategoriyalar yaratildi

 Mahsulotlar (SKU / QR / birlik) kiritildi

 Stock avtomatik yaratiladi

 Minimal qoldiq (min_stock) ishlaydi

 10 000+ mahsulot bilan ishlashga tayyor

5️⃣ QR / BARCODE SKANER

 USB QR skaner ulandi

 Skaner klaviatura (HID) sifatida ishlaydi

 QR o‘qilganda avtomatik Enter yuboriladi

 Mahsulot avtomatik topiladi

 Operator qo‘lda yozmaydi

6️⃣ FACE ID (OFFLINE)

 Face ID internet siz ishlaydi

 Xodim ro‘yxatdan o‘tkazildi (10–30 kadr)

 Rasmlar bazada saqlanmaydi

 Yuz ma’lumoti raqamli model (model.yml) ko‘rinishida

 Face ID tasdiqsiz harakat (kirim/chiqim) bo‘lmaydi

 Tasdiq 5 daqiqa amal qiladi

7️⃣ KIRIM / CHIQIM JARAYONI

 Kirim (IN) ishlaydi

 Chiqim (OUT) ishlaydi

 Yetarli qoldiq bo‘lmasa chiqim bloklanadi

 Har bir harakat xodim + foydalanuvchi bilan bog‘langan

 Harakatlar tarixda saqlanadi

 Bekor qilish (reversal) faqat Admin uchun

8️⃣ BACKUP (ZAXIRA)

 PostgreSQL backup pg_dump orqali

 .sql fayl sifatida saqlanadi

 Backup papkasi mavjud

 pg_dump versiyasi PostgreSQL bilan mos

 (ixtiyoriy) Avtomatik kunlik backup

9️⃣ QURILMALAR TEKSHIRUVI

 Ombor kompyuteri (SSD, 8GB RAM)

 Web kamera (720p yoki 1080p)

 USB QR skaner

 UPS (tavsiya etiladi)

 Tashqi backup disk (ixtiyoriy)

🔐 10️⃣ XAVFSIZLIK

 Lokal ishlash (internet shart emas)

 Face ID bilan tasdiqlash

 Rollar bo‘yicha ruxsat

 Session timeout

 Backup mavjud

📘 11️⃣ BUYURTMACHI UCHUN QISQA YO‘RIQNOMA

Ombor ishchisi:

QR skanerlaydi

Kamera qarshisida turadi

Face ID tasdiqlanadi

Harakat saqlanadi

Admin:

Foydalanuvchi qo‘shadi

Mahsulot kiritadi

Hisobot ko‘radi

Backup oladi

🟢 YAKUNIY XULOSA

Tizim to‘liq lokal ishlaydi, internet talab qilmaydi. Ombor uchun oddiy va ishonchli qurilmalar bilan ishlaydi. Ma’lumotlar xavfsiz saqlanadi va zaxira nusxasi mavjud.