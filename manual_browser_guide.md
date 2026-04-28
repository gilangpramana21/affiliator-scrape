# Manual Browser + API Approach

## Kenapa Approach Ini?

Playwright **SELALU** kena detection Tokopedia:
- "Coba lagi" page
- Row click tidak work
- Detail page tidak buka
- Contact info tidak bisa di-extract

**Solusi:** Pakai browser biasa (bukan automation) + HTTP requests

---

## Step-by-Step Guide:

### Step 1: Buka Chrome Biasa
1. Buka Google Chrome (bukan dari Playwright)
2. Navigate ke: https://affiliate-id.tokopedia.com/connection/creator?shop_region=ID&shop_id=7495177173399997259
3. Login kalau perlu
4. Pastikan kamu bisa lihat creator list

### Step 2: Copy Cookies dari DevTools
1. Tekan `F12` atau `Cmd+Option+I` untuk buka DevTools
2. Go to **Application** tab
3. Klik **Cookies** di sidebar kiri
4. Klik `https://affiliate-id.tokopedia.com`
5. Kamu akan lihat list cookies
6. Copy semua cookies (atau export dengan extension)

### Step 3: Save Cookies
Simpan cookies ke `config/cookies_manual.json` dengan format:
```json
[
  {
    "name": "sessionid",
    "value": "...",
    "domain": ".tokopedia.com",
    "path": "/",
    "httpOnly": true,
    "secure": false
  },
  ...
]
```

### Step 4: Test dengan HTTP Requests
Jalankan script yang pakai `requests` library (bukan Playwright):
```bash
python scrape_with_requests.py
```

---

## Keuntungan Approach Ini:

✅ **Tidak kena detection** - Pakai browser biasa untuk login
✅ **Cookies valid** - Dari browser real, bukan automation
✅ **Faster** - HTTP requests lebih cepat dari browser automation
✅ **Reliable** - Tidak ada "Coba lagi" atau blocking
✅ **Contact data accessible** - Bisa extract dari HTML response

---

## Kekurangan:

❌ **Manual step** - Perlu buka browser manual untuk get cookies
❌ **Cookies expire** - Perlu refresh cookies setiap beberapa hari
❌ **No JavaScript** - Kalau data di-load via JS, tidak bisa extract

---

## Alternative: Undetected ChromeDriver

Kalau mau tetap pakai automation tapi bypass detection:
```bash
pip install undetected-chromedriver
```

Library ini specifically designed untuk bypass detection.

