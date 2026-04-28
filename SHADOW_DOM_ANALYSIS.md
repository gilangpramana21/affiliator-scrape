# Shadow DOM Analysis & Strategy untuk Tokopedia Affiliate Scraper

## 🔍 Apa itu Shadow DOM?

### Definisi
Shadow DOM adalah fitur Web Components yang memungkinkan developer untuk **encapsulate** (menyembunyikan) struktur HTML, CSS, dan JavaScript dari main document. Ini seperti "kotak tertutup" di dalam halaman web.

### Contoh Shadow DOM
```html
<!-- Regular DOM (bisa diakses biasa) -->
<div class="user-card">
  <span>Username: John</span>
</div>

<!-- Shadow DOM (tersembunyi) -->
<user-profile>
  #shadow-root (open)
    <div class="profile">
      <span>Email: john@example.com</span>
    </div>
</user-profile>
```

### Karakteristik Shadow DOM
1. **Tidak bisa diakses dengan `document.querySelector()`** biasa
2. **Tidak bisa diakses dengan HTTP requests** (butuh JavaScript execution)
3. **Bisa diakses dengan JavaScript** jika `mode: "open"`
4. **Tidak bisa diakses sama sekali** jika `mode: "closed"`

---

## 🎯 Analisis Tokopedia Affiliate Center

### Hasil Investigasi Saya

Setelah analisis file `detail_page_with_contacts.html`, saya menemukan:

#### ❌ BUKAN Shadow DOM!
```html
<!-- Ini yang saya temukan di HTML -->
<span class="text-body-l-regular">WhatsApp:&nbsp;</span>
<div class="arco-typography text-body-l-medium">8153710996</div>

<span class="text-body-l-regular">Email:&nbsp;</span>
<div class="arco-typography text-body-l-medium">Genrosesfirda@gmail.com</div>
```

**Kesimpulan**: Kontak ada di **Regular DOM**, BUKAN Shadow DOM!

#### Kenapa Kamu Bilang Shadow DOM?

Kemungkinan:
1. **Konten di-load via JavaScript** (AJAX/Fetch) → Terlihat seperti Shadow DOM tapi bukan
2. **Konten di-render setelah page load** → Butuh wait for element
3. **Konten di-protect dengan obfuscation** → Terlihat susah diakses
4. **Popup/Modal** → Konten muncul setelah click button

---

## 🔧 Strategi Scraping: 3 Pendekatan

### Pendekatan 1: Browser Automation (Playwright/Selenium) ✅ RECOMMENDED

#### Kapan Digunakan?
- ✅ Konten di-load via JavaScript
- ✅ Ada CAPTCHA yang perlu di-solve
- ✅ Konten di-render setelah interaction (click, scroll, etc)
- ✅ Ada Shadow DOM (bisa diakses dengan JavaScript)

#### Kelebihan
- ✅ Bisa execute JavaScript → akses Shadow DOM
- ✅ Bisa handle CAPTCHA (manual atau auto)
- ✅ Bisa simulate user behavior (click, scroll, type)
- ✅ Bisa wait for dynamic content

#### Kekurangan
- ❌ Lebih lambat (butuh launch browser)
- ❌ Lebih banyak resource (memory, CPU)
- ❌ Lebih mudah terdeteksi (tapi bisa diatasi dengan stealth)

#### Cara Akses Shadow DOM dengan Playwright
```javascript
// JavaScript yang dijalankan di browser
const shadowHost = document.querySelector('user-profile');
const shadowRoot = shadowHost.shadowRoot; // Akses shadow root
const email = shadowRoot.querySelector('.email'); // Query di dalam shadow
```

#### Implementasi untuk Tokopedia
```python
# scrape_with_browser.py (sudah dibuat)
async def extract_contacts(self, page: Page):
    # Wait for content to load
    await page.wait_for_selector('span.text-body-l-regular')
    
    # Execute JavaScript to extract
    contacts = await page.evaluate("""
        () => {
            // Cari WhatsApp
            const waElements = document.querySelectorAll('span.text-body-l-regular');
            for (const el of waElements) {
                if (el.textContent.includes('WhatsApp:')) {
                    const parent = el.parentElement;
                    const numberEl = parent.querySelector('.arco-typography.text-body-l-medium');
                    return numberEl.textContent;
                }
            }
        }
    """)
```

---

### Pendekatan 2: HTTP Requests + HTML Parsing ❌ TIDAK BISA

#### Kapan Digunakan?
- ✅ Konten sudah ada di HTML response
- ✅ Tidak ada JavaScript rendering
- ✅ Tidak ada CAPTCHA
- ✅ Tidak ada Shadow DOM

#### Kelebihan
- ✅ Sangat cepat
- ✅ Resource minimal
- ✅ Mudah di-scale

#### Kekurangan
- ❌ **TIDAK BISA akses Shadow DOM** (butuh JavaScript)
- ❌ **TIDAK BISA handle CAPTCHA**
- ❌ **TIDAK BISA akses konten yang di-load via JavaScript**

#### Kenapa Tidak Bisa untuk Tokopedia?
```python
# Ini TIDAK AKAN WORK jika konten di-load via JavaScript
import requests
from lxml import html

response = requests.get(url, cookies=cookies)
doc = html.fromstring(response.text)

# Jika konten di-load via JavaScript, HTML response akan kosong!
contacts = doc.xpath('//span[contains(text(), "WhatsApp:")]')
# Result: [] (empty) karena konten belum di-render
```

---

### Pendekatan 3: Hybrid (Network Monitoring + DOM) ✅ OPTIMAL

#### Konsep
Gunakan browser automation TAPI monitor network requests untuk intercept API calls.

#### Kelebihan
- ✅ Lebih cepat dari pure DOM scraping
- ✅ Bisa dapat data langsung dari API
- ✅ Fallback ke DOM jika API tidak ada
- ✅ Bisa handle CAPTCHA

#### Implementasi
```python
# production_scraper_v2.py (sudah dibuat)
async def setup_network_monitoring(self, page):
    async def handle_response(response):
        url = response.url
        # Intercept API calls
        if 'api' in url and 'creator' in url:
            data = await response.json()
            # Extract contacts dari API response
            self.network_responses.append(data)
    
    page.on('response', handle_response)

# Kemudian extract dari network responses
contacts = self._extract_from_network_responses()

# Jika gagal, fallback ke DOM
if not contacts:
    contacts = await self._extract_from_dom(page)
```

---

## 🎯 Strategi yang Tepat untuk Tokopedia

### Rekomendasi: Hybrid Approach (Pendekatan 3)

#### Alasan
1. **Ada CAPTCHA** → Butuh browser automation
2. **Konten di-load via JavaScript** → Butuh JavaScript execution
3. **Mungkin ada API calls** → Bisa intercept untuk faster extraction
4. **Konten di Regular DOM** → Bisa extract dengan JavaScript

#### Flow Chart
```
┌─────────────────────────────────────────────────────────┐
│ 1. Launch Browser dengan Stealth Mode                  │
│    - Playwright dengan anti-detection                  │
│    - Load cookies untuk bypass login                   │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│ 2. Navigate ke List Page                                │
│    - Setup network monitoring                           │
│    - Wait for page load                                 │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│ 3. Check for CAPTCHA                                    │
│    - Jika ada: Pause dan tunggu user solve manual      │
│    - Jika tidak: Continue                               │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│ 4. Extract List of Creators                             │
│    - Click pada creator row                             │
│    - Wait for detail page                               │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│ 5. Extract Contacts (Hybrid)                            │
│    ┌─────────────────────────────────────────────────┐ │
│    │ A. Try Network Monitoring First                 │ │
│    │    - Check captured API responses               │ │
│    │    - Extract contacts dari JSON                 │ │
│    └─────────────────────────────────────────────────┘ │
│                          │                              │
│                          ▼                              │
│    ┌─────────────────────────────────────────────────┐ │
│    │ B. Fallback to DOM Extraction                   │ │
│    │    - Execute JavaScript di browser              │ │
│    │    - Query selectors untuk WhatsApp & Email    │ │
│    │    - Normalize phone number                     │ │
│    └─────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│ 6. Save Results & Continue                              │
│    - Save to JSON                                       │
│    - Add delay (3 seconds)                              │
│    - Next creator                                       │
└─────────────────────────────────────────────────────────┘
```

---

## 🛠️ Implementasi Detail

### File yang Sudah Dibuat

#### 1. `scrape_with_browser.py` - Simple Browser Scraper
**Fitur:**
- ✅ Playwright dengan stealth mode
- ✅ Manual CAPTCHA solving
- ✅ DOM extraction untuk contacts
- ✅ Cookie loading

**Kapan Digunakan:**
- Testing awal
- Scraping kecil (<100 affiliators)
- Debugging extraction logic

#### 2. `production_scraper_v2.py` - Production Scraper
**Fitur:**
- ✅ Network monitoring (intercept API calls)
- ✅ Hybrid extraction (Network + DOM)
- ✅ Statistics tracking
- ✅ CAPTCHA detection
- ✅ Error handling

**Kapan Digunakan:**
- Production scraping (1000+ affiliators)
- Daily scraping
- Optimal performance

---

## 🔐 Anti-Detection Strategy

### Masalah: Browser Automation Terdeteksi

#### Tanda-tanda Terdeteksi
1. **"Coba lagi" blocking page**
2. **CAPTCHA muncul terus-menerus**
3. **Request di-block (403 Forbidden)**
4. **Redirect ke login page**

#### Solusi: Stealth Mode

##### 1. Fingerprint Randomization
```python
# src/anti_detection/browser_engine.py
fingerprint = BrowserFingerprint(
    user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)...",
    platform="MacIntel",
    screen_resolution=(1920, 1080),
    viewport_size=(1400, 900),
    timezone="Asia/Jakarta",
    # ... dll
)
```

##### 2. JavaScript Patches
```javascript
// Patch navigator.webdriver
Object.defineProperty(navigator, 'webdriver', {
    get: () => undefined
});

// Patch chrome.runtime
Object.defineProperty(window.chrome, 'runtime', {
    get: () => undefined
});
```

##### 3. Behavioral Simulation
```python
# Random delays
await asyncio.sleep(random.uniform(2, 5))

# Random mouse movements
await page.mouse.move(random.randint(100, 800), random.randint(100, 600))

# Random scrolling
await page.evaluate(f"window.scrollBy(0, {random.randint(200, 800)})")
```

---

## 📊 Perbandingan Pendekatan

| Aspek | HTTP Only | Browser Only | Hybrid |
|-------|-----------|--------------|--------|
| **Speed** | ⚡⚡⚡ Sangat Cepat | 🐌 Lambat | ⚡⚡ Cepat |
| **Resource** | 💚 Minimal | 🔴 Tinggi | 🟡 Sedang |
| **CAPTCHA** | ❌ Tidak Bisa | ✅ Bisa | ✅ Bisa |
| **Shadow DOM** | ❌ Tidak Bisa | ✅ Bisa | ✅ Bisa |
| **JavaScript Content** | ❌ Tidak Bisa | ✅ Bisa | ✅ Bisa |
| **Detection Risk** | 💚 Rendah | 🟡 Sedang | 🟡 Sedang |
| **Scalability** | ⚡⚡⚡ Sangat Baik | 🐌 Terbatas | ⚡⚡ Baik |
| **Complexity** | 💚 Simple | 🟡 Sedang | 🔴 Complex |

---

## 🎯 Kesimpulan & Rekomendasi

### Untuk Tokopedia Affiliate Center

#### ✅ Gunakan: Hybrid Approach (production_scraper_v2.py)

**Alasan:**
1. **Konten di Regular DOM** (bukan Shadow DOM) → Bisa extract dengan JavaScript
2. **Ada CAPTCHA** → Butuh browser automation
3. **Mungkin ada API calls** → Network monitoring bisa lebih cepat
4. **Need scale to 1000+** → Hybrid lebih optimal dari pure browser

#### 📋 Action Plan

**Phase 1: Testing (Sekarang)**
```bash
# Test dengan simple scraper dulu
python test_shadow_dom_scraper.py
```
- Verify DOM extraction works
- Check CAPTCHA frequency
- Measure success rate

**Phase 2: Optimization (Jika Test Berhasil)**
```bash
# Switch ke production scraper
python quick_test.py  # 10 affiliators
```
- Enable network monitoring
- Measure speed improvement
- Compare success rates

**Phase 3: Production (Jika Optimization OK)**
```bash
# Full production run
python production_scraper_v2.py  # 1000+ affiliators
```
- Monitor for blocking
- Adjust delays if needed
- Consider proxy rotation

---

## 🚨 Catatan Penting

### Tentang Shadow DOM
**Kesimpulan dari analisis HTML:**
- ❌ Tokopedia **TIDAK menggunakan Shadow DOM** untuk kontak
- ✅ Kontak ada di **Regular DOM** dengan class `arco-typography text-body-l-medium`
- ✅ Bisa diakses dengan **JavaScript biasa** (tidak perlu pierce shadow root)

### Tentang "Tidak Bisa Pake Playwright"
**Klarifikasi:**
- ❌ Playwright **BISA** digunakan untuk Tokopedia
- ✅ Yang **TIDAK BISA** adalah HTTP-only approach (requests library)
- ✅ Playwright **DIPERLUKAN** karena:
  1. Konten di-load via JavaScript
  2. Ada CAPTCHA
  3. Butuh cookie management
  4. Butuh stealth mode

### Kenapa Context Bilang "Tidak Bisa"?
Kemungkinan maksudnya:
- "Tidak bisa pake Playwright **TANPA stealth mode**" → Akan terdeteksi
- "Tidak bisa pake **HTTP requests**" → Konten tidak ada di HTML response
- "Tidak bisa pake **headless mode**" → CAPTCHA perlu di-solve manual

---

## 📚 Resources

### Dokumentasi
- [Playwright Shadow DOM](https://playwright.dev/docs/selectors#pierce-shadow-dom)
- [Web Components Shadow DOM](https://developer.mozilla.org/en-US/docs/Web/Web_Components/Using_shadow_DOM)
- [Playwright Stealth](https://github.com/berstend/puppeteer-extra/tree/master/packages/puppeteer-extra-plugin-stealth)

### Tools untuk Debug
```javascript
// Check if element has shadow root
const el = document.querySelector('user-profile');
console.log(el.shadowRoot); // null jika tidak ada shadow DOM

// List all shadow roots in page
document.querySelectorAll('*').forEach(el => {
    if (el.shadowRoot) {
        console.log('Shadow root found:', el);
    }
});
```

---

**Kesimpulan Akhir:**
- ✅ Gunakan **Playwright dengan stealth mode**
- ✅ Kontak di **Regular DOM** (bukan Shadow DOM)
- ✅ Hybrid approach untuk **optimal performance**
- ✅ Manual CAPTCHA solving (atau integrate CapSolver nanti)
- ✅ Start testing dengan `test_shadow_dom_scraper.py`
