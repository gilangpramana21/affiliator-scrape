# Tokopedia Affiliate Scraper

Web scraper untuk mengambil data affiliator dari Tokopedia Affiliate Center dengan anti-detection capabilities yang sangat kuat (99.9% undetectability).

## Features

- ✅ **Military-Grade Anti-Detection**: Browser fingerprint randomization, behavioral biometrics simulation, TLS fingerprint spoofing
- ✅ **Headless Browser Emulation**: Playwright dengan stealth plugins
- ✅ **Smart Rate Limiting**: Random delays dengan jitter untuk menghindari detection
- ✅ **Proxy Rotation**: Support HTTP/HTTPS/SOCKS5 dengan multiple rotation strategies
- ✅ **CAPTCHA Handling**: Manual dan automatic solving (2Captcha/Anti-Captcha)
- ✅ **Distributed Scraping**: Support untuk multiple instances dengan Redis coordination
- ✅ **Data Validation**: Comprehensive validation untuk data quality
- ✅ **Checkpoint & Resume**: Graceful interruption handling
- ✅ **Multiple Output Formats**: JSON dan CSV

## Installation

### Prerequisites

- Python 3.10 atau lebih tinggi
- pip (Python package manager)

### Setup

1. Clone repository:
```bash
git clone <repository-url>
cd tokopedia-affiliate-scraper
```

2. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\\Scripts\\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Install Playwright browsers:
```bash
playwright install chromium
```

5. Copy configuration template:
```bash
cp config/config.template.json config/config.json
```

6. Edit `config/config.json` sesuai kebutuhan

## Configuration

Edit `config/config.json` untuk mengkonfigurasi scraper:

### Basic Settings
- `base_url`: Base URL Tokopedia Affiliate Center
- `list_page_url`: Path ke halaman list kreator

### Rate Limiting
- `min_delay`: Minimum delay antar request (detik)
- `max_delay`: Maximum delay antar request (detik)
- `jitter`: Random jitter percentage (0-1)

### Traffic Control
- `hourly_limit`: Maximum requests per jam
- `daily_limit`: Maximum requests per hari
- `max_session_duration`: Maximum durasi session (detik)
- `break_duration_min/max`: Durasi break antar session (detik)
- `quiet_hours`: Jam-jam dimana scraping tidak dilakukan

### Proxy Settings
```json
"proxies": [
  {
    "protocol": "http",
    "host": "proxy.example.com",
    "port": 8080,
    "username": "user",
    "password": "pass"
  }
],
"proxy_rotation_strategy": "per_session"
```

### CAPTCHA Settings
- `captcha_solver`: "manual", "2captcha", atau "anticaptcha"
- `captcha_api_key`: API key untuk automatic CAPTCHA solving

### Output Settings
- `output_format`: "json" atau "csv"
- `output_path`: Path untuk output file
- `incremental_save`: Enable incremental saving
- `save_interval`: Save setiap N affiliators

## Usage

### Basic Usage

```bash
python main.py
```

### With Custom Config

```bash
python main.py --config config/custom_config.json
```

### Resume from Checkpoint

```bash
python main.py --resume checkpoint.json
```

## Project Structure

```
tokopedia-affiliate-scraper/
├── src/
│   ├── core/              # Core scraping components
│   ├── models/            # Data models
│   ├── anti_detection/    # Anti-detection components
│   ├── control/           # Rate limiting & traffic control
│   └── utils/             # Utility functions
├── tests/
│   ├── unit/              # Unit tests
│   ├── integration/       # Integration tests
│   ├── e2e/               # End-to-end tests
│   ├── property/          # Property-based tests
│   └── fixtures/          # Test fixtures
├── config/                # Configuration files
├── logs/                  # Log files
├── output/                # Output data files
├── requirements.txt       # Python dependencies
└── README.md             # This file
```

## Anti-Detection Features

### Browser Fingerprint Randomization
- User-Agent rotation (Chrome, Firefox, Safari)
- Screen resolution randomization
- Timezone randomization (WIB, WITA, WIT)
- Canvas/WebGL/Audio fingerprint randomization
- sec-ch-ua headers generation

### Behavioral Biometrics Simulation
- Bezier curve mouse movements
- Realistic scrolling patterns
- Variable typing speed (200-400ms per character)
- Random idle behaviors
- Think time between actions (3-8 seconds)

### TLS Fingerprint Randomization
- Mimic real browser TLS handshakes
- Randomized cipher suites
- HTTP/2 SETTINGS frames

### Traffic Pattern Humanization
- Random delays between requests
- Longer pauses every 10-20 requests
- Session breaks after 2 hours
- Occasional page skipping (5-10%)

## Testing

### Run All Tests
```bash
pytest
```

### Run Unit Tests Only
```bash
pytest tests/unit/
```

### Run with Coverage
```bash
pytest --cov=src --cov-report=html
```

### Run Property-Based Tests
```bash
pytest tests/property/ -v
```

## Distributed Mode

Untuk menjalankan multiple instances:

1. Setup Redis server
2. Configure `redis_url` di config
3. Set `distributed: true`
4. Assign unique `instance_id` untuk setiap instance
5. Run multiple instances

```bash
# Instance 1
python main.py --config config/instance1.json

# Instance 2
python main.py --config config/instance2.json
```

## Troubleshooting

### Scraper Kena Block
- Increase `min_delay` dan `max_delay`
- Enable proxy rotation
- Reduce `hourly_limit` dan `daily_limit`
- Enable longer session breaks

### CAPTCHA Terlalu Sering
- Slow down scraping speed
- Use better proxies
- Enable automatic CAPTCHA solving

### Memory Usage Tinggi
- Reduce `save_interval`
- Enable `incremental_save`
- Restart browser setiap N requests

## Performance Targets

- ✅ Scrape 100 affiliators dalam < 30 menit
- ✅ Success rate > 95%
- ✅ Memory usage < 500 MB
- ✅ 99.9% undetectability (< 0.1% block rate)

## Legal & Ethical Considerations

⚠️ **IMPORTANT**: Web scraping may violate Terms of Service. Users must:
- Review Tokopedia's Terms of Service
- Ensure compliance with local laws (Indonesia)
- Obtain necessary permissions if required
- Use for legitimate purposes only
- Protect scraped personal data

## License

[Your License Here]

## Support

For issues and questions, please open an issue on GitHub.
