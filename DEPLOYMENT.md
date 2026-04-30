# 🚀 Deployment Guide - Tokopedia Affiliator Dashboard

Panduan lengkap untuk deploy web dashboard ke berbagai platform.

---

## 📋 Prerequisites

Sebelum deploy, pastikan:
- ✅ Python 3.8+ terinstall
- ✅ Git terinstall
- ✅ Akun di platform deployment (Heroku/Railway/Render)

---

## 🏠 Local Development

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Install Playwright (untuk scraping)

```bash
pip install playwright
playwright install chromium
```

### 3. Run Dashboard

```bash
python app.py
```

Dashboard akan berjalan di: **http://localhost:5000**

---

## ☁️ Deploy ke Railway (Recommended)

Railway adalah platform deployment modern yang mudah dan gratis untuk project kecil.

### Step 1: Persiapan

1. Buat akun di [Railway.app](https://railway.app)
2. Install Railway CLI (optional):
   ```bash
   npm install -g @railway/cli
   ```

### Step 2: Buat File Konfigurasi

Buat file `railway.json`:

```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "python app.py",
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

Buat file `Procfile`:

```
web: python app.py
```

### Step 3: Deploy

**Via Web UI:**
1. Login ke Railway
2. Klik "New Project" → "Deploy from GitHub repo"
3. Pilih repository ini
4. Railway akan auto-detect Python dan deploy

**Via CLI:**
```bash
railway login
railway init
railway up
```

### Step 4: Set Environment Variables (Optional)

Di Railway dashboard:
- `FLASK_ENV=production`
- `PORT=5000`

---

## 🚂 Deploy ke Heroku

### Step 1: Install Heroku CLI

```bash
# macOS
brew tap heroku/brew && brew install heroku

# Windows
# Download dari https://devcenter.heroku.com/articles/heroku-cli
```

### Step 2: Login

```bash
heroku login
```

### Step 3: Buat File Konfigurasi

Buat file `Procfile`:

```
web: python app.py
```

Buat file `runtime.txt`:

```
python-3.11.0
```

### Step 4: Deploy

```bash
# Create Heroku app
heroku create tokopedia-affiliator-dashboard

# Deploy
git push heroku main

# Open app
heroku open
```

### Step 5: Set Environment Variables

```bash
heroku config:set FLASK_ENV=production
```

---

## 🎨 Deploy ke Render

### Step 1: Persiapan

1. Buat akun di [Render.com](https://render.com)
2. Connect GitHub repository

### Step 2: Buat Web Service

1. Dashboard → "New" → "Web Service"
2. Connect repository
3. Konfigurasi:
   - **Name**: tokopedia-affiliator
   - **Environment**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python app.py`
   - **Instance Type**: Free

### Step 3: Environment Variables

Tambahkan di Render dashboard:
- `FLASK_ENV=production`
- `PORT=5000`

---

## 🐳 Deploy dengan Docker

### Step 1: Buat Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright
RUN pip install playwright
RUN playwright install chromium
RUN playwright install-deps chromium

# Copy application
COPY . .

# Create output directory
RUN mkdir -p output

EXPOSE 5000

CMD ["python", "app.py"]
```

### Step 2: Build & Run

```bash
# Build image
docker build -t tokopedia-dashboard .

# Run container
docker run -p 5000:5000 -v $(pwd)/output:/app/output tokopedia-dashboard
```

### Step 3: Deploy ke Docker Hub

```bash
# Tag image
docker tag tokopedia-dashboard yourusername/tokopedia-dashboard

# Push to Docker Hub
docker push yourusername/tokopedia-dashboard
```

---

## 🔧 Production Configuration

### 1. Update app.py untuk Production

Ubah baris terakhir di `app.py`:

```python
if __name__ == '__main__':
    import os
    
    # Create directories
    Path("output").mkdir(exist_ok=True)
    Path("templates").mkdir(exist_ok=True)
    
    # Get port from environment (for cloud platforms)
    port = int(os.environ.get('PORT', 5000))
    
    # Production mode
    debug = os.environ.get('FLASK_ENV') != 'production'
    
    print("\n" + "="*80)
    print("🚀 TOKOPEDIA AFFILIATOR DASHBOARD")
    print("="*80)
    print(f"\n📊 Dashboard running on port: {port}")
    print(f"🔧 Debug mode: {debug}")
    print("\n⚠️  IMPORTANT:")
    print("   - Solve CAPTCHA manually when scraping")
    print("   - Dashboard will show progress")
    print("   - Data auto-saved to Excel\n")
    print("="*80 + "\n")
    
    app.run(debug=debug, host='0.0.0.0', port=port)
```

### 2. Tambah .gitignore

Pastikan file ini ada di `.gitignore`:

```
# Output files
output/
*.xlsx
*.json

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
env/

# Config
config/cookies.json
config/config.json

# IDE
.vscode/
.idea/
```

---

## 📊 Monitoring & Logs

### Railway
```bash
railway logs
```

### Heroku
```bash
heroku logs --tail
```

### Render
- Lihat logs di dashboard Render

---

## ⚠️ Important Notes

### 1. Scraping di Production

**PERHATIAN**: Scraping dengan Playwright membutuhkan browser headless. Di cloud platform:
- ✅ **Railway**: Support Playwright dengan Nixpacks
- ✅ **Render**: Support dengan buildpack khusus
- ⚠️ **Heroku**: Perlu buildpack tambahan

### 2. Manual CAPTCHA

Karena scraping membutuhkan manual CAPTCHA solving:
- Dashboard **HANYA untuk monitoring** di production
- Scraping sebaiknya dilakukan **di local machine**
- Upload hasil scraping ke server via API (future feature)

### 3. Storage

Platform gratis biasanya **ephemeral storage**:
- File di `/output` akan hilang saat restart
- Gunakan cloud storage (S3, Google Cloud Storage) untuk persistent storage
- Atau download Excel setelah scraping selesai

---

## 🔐 Security Best Practices

1. **Jangan commit cookies.json**
   ```bash
   echo "config/cookies.json" >> .gitignore
   ```

2. **Set SECRET_KEY untuk Flask**
   ```python
   app.secret_key = os.environ.get('SECRET_KEY', 'dev-key-change-in-production')
   ```

3. **Rate Limiting** (optional)
   ```bash
   pip install flask-limiter
   ```

4. **Authentication** (optional untuk production)
   - Tambahkan login page
   - Gunakan Flask-Login atau JWT

---

## 🆘 Troubleshooting

### Error: "Port already in use"
```bash
# Kill process on port 5000
lsof -ti:5000 | xargs kill -9
```

### Error: "Playwright not found"
```bash
pip install playwright
playwright install chromium
```

### Error: "Permission denied" di Docker
```bash
# Run with sudo
sudo docker run ...
```

### Error: "Module not found"
```bash
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

---

## 📚 Resources

- [Railway Docs](https://docs.railway.app)
- [Heroku Python Guide](https://devcenter.heroku.com/articles/getting-started-with-python)
- [Render Docs](https://render.com/docs)
- [Flask Deployment](https://flask.palletsprojects.com/en/2.3.x/deploying/)
- [Playwright Docs](https://playwright.dev/python/)

---

## 🎯 Next Steps

Setelah deploy:
1. ✅ Test dashboard di browser
2. ✅ Test scraping (di local)
3. ✅ Download hasil Excel
4. ✅ Setup monitoring/alerts
5. ✅ Backup data secara berkala

---

**Happy Deploying! 🚀**
