# Setup Webshare.io Proxy

## Step 1: Register

1. Buka: https://www.webshare.io/
2. Klik "Sign Up" atau "Get Started Free"
3. Register dengan email Anda
4. Verify email

## Step 2: Get Free Proxies

1. Login ke dashboard: https://proxy.webshare.io/
2. Klik "Proxy" → "Proxy List"
3. Anda akan dapat **10 free proxies**
4. Download proxy list (format: IP:PORT:USERNAME:PASSWORD)

## Step 3: Copy Credentials

Format proxy dari Webshare:
```
IP:PORT:USERNAME:PASSWORD
```

Contoh:
```
154.16.146.43:80:username123:password456
45.95.96.132:8080:username123:password456
```

## Step 4: Paste ke Config

Setelah dapat proxy list, paste ke file `config/webshare_proxies.txt`

Format per line:
```
IP:PORT:USERNAME:PASSWORD
```

## Alternative: Smartproxy

Jika Webshare tidak cocok, gunakan Smartproxy:

1. Register: https://smartproxy.com/
2. Free trial: 3-day trial dengan 100MB
3. Pilih: Residential Proxies → Indonesia
4. Get credentials dari dashboard

## Alternative: ProxyScrape

Jika mau yang benar-benar gratis (tapi kurang reliable):

1. Buka: https://proxyscrape.com/free-proxy-list
2. Filter: Country = Indonesia, Protocol = HTTP/HTTPS
3. Download proxy list
4. Test proxy satu-satu (banyak yang tidak work)

## Recommendation

**Untuk production:** Gunakan Webshare.io (free tier) atau Smartproxy (trial)
**Untuk testing:** Webshare.io free tier sudah cukup
