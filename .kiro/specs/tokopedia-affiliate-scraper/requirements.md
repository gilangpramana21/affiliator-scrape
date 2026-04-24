# Requirements Document

## Introduction

Tokopedia Affiliate Scraper adalah program web scraper yang mengambil data affiliator dari Seller Center Tokopedia (Affiliate Center). Program ini akan mengekstrak informasi kreator/affiliator dari halaman daftar dan halaman detail, termasuk data kontak mereka, tanpa menggunakan API resmi Tokopedia.

## Glossary

- **Scraper**: Komponen utama yang melakukan web scraping
- **HTTP_Client**: Komponen yang menangani HTTP requests ke Tokopedia
- **HTML_Parser**: Komponen yang mem-parse HTML response menjadi struktur data
- **Affiliator_Extractor**: Komponen yang mengekstrak data affiliator dari parsed HTML
- **Data_Store**: Komponen yang menyimpan hasil scraping
- **Rate_Limiter**: Komponen yang mengatur kecepatan request untuk menghindari blocking
- **Session_Manager**: Komponen yang mengelola session dan cookies
- **Affiliator**: Kreator yang terdaftar di Affiliate Center Tokopedia
- **Creator_List_Page**: Halaman yang menampilkan daftar affiliator
- **Creator_Detail_Page**: Halaman yang menampilkan detail lengkap seorang affiliator
- **Affiliator_Data**: Struktur data yang berisi informasi affiliator (username, kategori, pengikut, GMV, produk terjual, rata-rata tayangan, tingkat interaksi, nomor kontak)

## Requirements

### Requirement 1: HTTP Request Management

**User Story:** As a developer, I want to send HTTP requests to Tokopedia pages, so that I can retrieve HTML content for scraping.

#### Acceptance Criteria

1. WHEN a valid URL is provided, THE HTTP_Client SHALL send a GET request and return the response
2. WHEN a request fails with a network error, THE HTTP_Client SHALL retry up to 3 times with exponential backoff
3. WHEN a request receives a 429 status code, THE HTTP_Client SHALL wait for the specified retry-after duration before retrying
4. THE HTTP_Client SHALL include realistic browser headers (User-Agent, Accept, Accept-Language) in all requests
5. THE HTTP_Client SHALL maintain cookies across requests within the same session
6. WHEN a request timeout occurs after 30 seconds, THE HTTP_Client SHALL return a timeout error

### Requirement 2: Rate Limiting

**User Story:** As a developer, I want to control request frequency, so that I can avoid being blocked by Tokopedia's anti-scraping measures.

#### Acceptance Criteria

1. THE Rate_Limiter SHALL enforce a minimum delay of 2 seconds between consecutive requests
2. WHEN multiple requests are queued, THE Rate_Limiter SHALL process them sequentially with the configured delay
3. THE Rate_Limiter SHALL allow configuration of delay duration at initialization
4. WHEN a request is made before the delay period expires, THE Rate_Limiter SHALL wait until the delay period completes

### Requirement 3: HTML Parsing

**User Story:** As a developer, I want to parse HTML responses, so that I can extract structured data from web pages.

#### Acceptance Criteria

1. WHEN valid HTML content is provided, THE HTML_Parser SHALL parse it into a queryable DOM structure
2. WHEN invalid or malformed HTML is provided, THE HTML_Parser SHALL parse it using error recovery mode
3. THE HTML_Parser SHALL support CSS selector queries on the parsed DOM
4. THE HTML_Parser SHALL support XPath queries on the parsed DOM
5. WHEN a selector matches no elements, THE HTML_Parser SHALL return an empty result set

### Requirement 4: Creator List Page Scraping

**User Story:** As a user, I want to scrape the creator list page, so that I can get a list of all available affiliators.

#### Acceptance Criteria

1. WHEN the creator list page URL is provided, THE Affiliator_Extractor SHALL extract all affiliator entries from the page
2. FOR EACH affiliator entry, THE Affiliator_Extractor SHALL extract username, kategori, pengikut count, GMV, produk terjual count, rata-rata tayangan, and tingkat interaksi
3. WHEN an affiliator entry has missing fields, THE Affiliator_Extractor SHALL mark those fields as null
4. THE Affiliator_Extractor SHALL extract the detail page URL for each affiliator
5. WHEN pagination exists, THE Affiliator_Extractor SHALL identify the next page URL
6. WHEN no more pages exist, THE Affiliator_Extractor SHALL return null for next page URL

### Requirement 5: Creator Detail Page Scraping

**User Story:** As a user, I want to scrape creator detail pages, so that I can get complete information including contact numbers.

#### Acceptance Criteria

1. WHEN a creator detail page URL is provided, THE Affiliator_Extractor SHALL extract the complete affiliator profile
2. THE Affiliator_Extractor SHALL extract the contact number (nomor kontak) from the detail page
3. WHEN a contact number is not available, THE Affiliator_Extractor SHALL mark it as null
4. THE Affiliator_Extractor SHALL extract all additional profile information available on the detail page
5. WHEN the detail page structure changes, THE Affiliator_Extractor SHALL log a parsing error with the page URL

### Requirement 6: Data Structure Validation

**User Story:** As a developer, I want to validate extracted data, so that I can ensure data quality and consistency.

#### Acceptance Criteria

1. WHEN Affiliator_Data is created, THE Scraper SHALL validate that username is a non-empty string
2. WHEN numeric fields (pengikut, GMV, produk terjual, rata-rata tayangan) are extracted, THE Scraper SHALL convert them to numeric types
3. WHEN tingkat interaksi is extracted, THE Scraper SHALL validate it is a percentage value between 0 and 100
4. WHEN a contact number is extracted, THE Scraper SHALL validate it matches Indonesian phone number format (starts with 08 or +62)
5. WHEN validation fails, THE Scraper SHALL log the validation error and mark the field as invalid

### Requirement 7: Data Storage

**User Story:** As a user, I want to save scraped data, so that I can use it for analysis or other purposes.

#### Acceptance Criteria

1. THE Data_Store SHALL support saving Affiliator_Data to JSON format
2. THE Data_Store SHALL support saving Affiliator_Data to CSV format
3. WHEN saving to JSON, THE Data_Store SHALL create a valid JSON array of all affiliator records
4. WHEN saving to CSV, THE Data_Store SHALL include headers and properly escape special characters
5. THE Data_Store SHALL support incremental saving (append mode) to avoid data loss on interruption
6. WHEN a file write fails, THE Data_Store SHALL return an error without losing in-memory data

### Requirement 8: Session Management

**User Story:** As a developer, I want to manage scraping sessions, so that I can maintain state and handle authentication if needed.

#### Acceptance Criteria

1. THE Session_Manager SHALL initialize a new session with empty cookies
2. THE Session_Manager SHALL persist cookies received from responses
3. THE Session_Manager SHALL include persisted cookies in subsequent requests
4. THE Session_Manager SHALL support loading cookies from a file for session restoration
5. THE Session_Manager SHALL support saving cookies to a file for session persistence
6. WHEN a session expires (detected by redirect to login), THE Session_Manager SHALL return a session expired error

### Requirement 9: Error Handling and Logging

**User Story:** As a developer, I want comprehensive error handling and logging, so that I can debug issues and monitor scraping progress.

#### Acceptance Criteria

1. WHEN any component encounters an error, THE Scraper SHALL log the error with timestamp, component name, and error details
2. THE Scraper SHALL log the start and completion of each scraping operation
3. THE Scraper SHALL log the number of affiliators successfully scraped
4. WHEN a page fails to scrape after all retries, THE Scraper SHALL log the failure and continue with the next page
5. THE Scraper SHALL support configurable log levels (DEBUG, INFO, WARNING, ERROR)
6. THE Scraper SHALL write logs to both console and a log file

### Requirement 10: Scraping Orchestration

**User Story:** As a user, I want to run a complete scraping operation, so that I can collect all affiliator data with a single command.

#### Acceptance Criteria

1. WHEN the scraper is started, THE Scraper SHALL scrape all pages of the creator list
2. FOR EACH affiliator found in the list, THE Scraper SHALL scrape the detail page to get the contact number
3. THE Scraper SHALL aggregate all Affiliator_Data into a single collection
4. WHEN scraping completes, THE Scraper SHALL save the aggregated data to the configured output format
5. THE Scraper SHALL report progress (e.g., "Scraped 50/200 affiliators") during execution
6. WHEN the scraper is interrupted (SIGINT), THE Scraper SHALL save partial results before exiting

### Requirement 11: Configuration Management

**User Story:** As a user, I want to configure scraper behavior, so that I can customize it for different use cases.

#### Acceptance Criteria

1. THE Scraper SHALL support configuration via a JSON configuration file
2. THE Scraper SHALL support configuration of: base URL, rate limit delay, request timeout, retry attempts, output format, output file path
3. WHEN a configuration file is not found, THE Scraper SHALL use default values
4. WHEN an invalid configuration value is provided, THE Scraper SHALL return a validation error with the invalid field name
5. THE Scraper SHALL validate all configuration values at startup before beginning scraping

### Requirement 12: Data Serialization Round-Trip

**User Story:** As a developer, I want to ensure data serialization is correct, so that I can reliably save and load affiliator data.

#### Acceptance Criteria

1. WHEN Affiliator_Data is serialized to JSON and then deserialized, THE Data_Store SHALL produce an equivalent Affiliator_Data object
2. WHEN Affiliator_Data is serialized to CSV and then parsed, THE Data_Store SHALL produce an equivalent Affiliator_Data object (excluding null values which may become empty strings)
3. FOR ALL valid Affiliator_Data objects, serializing then deserializing SHALL preserve all non-null field values
4. WHEN special characters exist in string fields, THE Data_Store SHALL properly escape and unescape them during serialization round-trip

### Requirement 13: Selector Robustness

**User Story:** As a developer, I want the scraper to handle HTML structure variations, so that minor page changes don't break the scraper.

#### Acceptance Criteria

1. THE Affiliator_Extractor SHALL use multiple fallback CSS selectors for each data field
2. WHEN the primary selector fails, THE Affiliator_Extractor SHALL try alternative selectors in order
3. WHEN all selectors fail for a field, THE Affiliator_Extractor SHALL mark the field as null and log a warning
4. THE Affiliator_Extractor SHALL extract text content with whitespace normalization (trim and collapse multiple spaces)
5. WHEN extracting numeric values with formatting (e.g., "1,234" or "1.2K"), THE Affiliator_Extractor SHALL parse them to numeric values

### Requirement 14: Anti-Detection Measures

**User Story:** As a developer, I want to avoid detection as a bot, so that the scraper can operate without being blocked by Tokopedia/TikTok anti-scraping systems.

#### Acceptance Criteria

1. THE HTTP_Client SHALL rotate User-Agent headers from a predefined list of realistic browser agents (Chrome, Firefox, Safari on Windows/Mac/Linux)
2. THE HTTP_Client SHALL include Accept-Language header with Indonesian locale (id-ID, id)
3. THE HTTP_Client SHALL include Referer header matching the previous page URL
4. THE Rate_Limiter SHALL add random jitter (±20%) to the delay between requests
5. WHEN making requests, THE HTTP_Client SHALL follow redirects automatically up to 5 hops
6. THE HTTP_Client SHALL include realistic browser headers: Accept, Accept-Encoding (gzip, deflate, br), Connection (keep-alive), DNT (1)
7. THE HTTP_Client SHALL randomize the order of HTTP headers to mimic real browser behavior
8. THE Session_Manager SHALL maintain a consistent User-Agent throughout a single scraping session
9. THE Rate_Limiter SHALL implement random delays between 2-5 seconds (not fixed intervals) to simulate human browsing patterns
10. THE HTTP_Client SHALL set viewport size headers (sec-ch-ua-mobile, sec-ch-viewport-width) to mimic real browser
11. WHEN scraping multiple pages, THE Scraper SHALL introduce longer random pauses (10-30 seconds) every 10-20 requests to simulate human reading time
12. THE HTTP_Client SHALL respect robots.txt directives if present (optional, configurable)
13. THE Scraper SHALL limit concurrent requests to 1 (sequential only) to avoid triggering rate limit detection

### Requirement 15: Data Deduplication

**User Story:** As a user, I want to avoid duplicate affiliator records, so that my dataset is clean and accurate.

#### Acceptance Criteria

1. WHEN an affiliator with the same username already exists in the collection, THE Scraper SHALL skip adding the duplicate
2. THE Scraper SHALL use username as the unique identifier for deduplication
3. WHEN a duplicate is detected, THE Scraper SHALL log a warning with the duplicate username
4. THE Scraper SHALL maintain a count of duplicates detected during the scraping session
5. WHEN scraping completes, THE Scraper SHALL report the total number of unique affiliators and duplicates found

### Requirement 16: IP Rotation and Proxy Support

**User Story:** As a developer, I want to use proxies and rotate IPs, so that I can avoid IP-based blocking from Tokopedia/TikTok.

#### Acceptance Criteria

1. THE HTTP_Client SHALL support HTTP/HTTPS proxy configuration
2. THE HTTP_Client SHALL support SOCKS5 proxy configuration
3. WHEN a proxy list is provided, THE HTTP_Client SHALL rotate proxies for each request or after N requests (configurable)
4. WHEN a proxy fails (connection timeout or error), THE HTTP_Client SHALL mark it as failed and try the next proxy
5. THE HTTP_Client SHALL support proxy authentication (username/password)
6. THE Scraper SHALL allow configuration of proxy rotation strategy: per-request, per-session, or per-N-requests
7. WHEN all proxies fail, THE HTTP_Client SHALL fall back to direct connection (configurable) or return an error
8. THE HTTP_Client SHALL validate proxy connectivity before starting scraping session

### Requirement 17: Browser Fingerprint Randomization

**User Story:** As a developer, I want to randomize browser fingerprints, so that each scraping session appears as a different user to anti-bot systems.

#### Acceptance Criteria

1. THE HTTP_Client SHALL generate realistic sec-ch-ua headers matching the selected User-Agent
2. THE HTTP_Client SHALL randomize screen resolution values (1920x1080, 1366x768, 1440x900, etc.)
3. THE HTTP_Client SHALL randomize timezone offset to match Indonesian timezones (WIB, WITA, WIT)
4. THE HTTP_Client SHALL include sec-ch-ua-platform header matching the User-Agent OS
5. WHEN starting a new session, THE Session_Manager SHALL generate a new consistent fingerprint set
6. THE HTTP_Client SHALL maintain fingerprint consistency within a single session (same User-Agent, same resolution, same timezone)

### Requirement 18: Request Pattern Humanization

**User Story:** As a developer, I want to mimic human browsing patterns, so that the scraper behavior is indistinguishable from real users.

#### Acceptance Criteria

1. WHEN navigating to a detail page, THE Scraper SHALL first visit the list page to establish a natural referrer chain
2. THE Scraper SHALL implement random "think time" between 3-8 seconds before clicking to detail pages
3. THE Scraper SHALL occasionally skip detail pages (5-10% of the time) to simulate users not clicking every item
4. WHEN scraping multiple pages, THE Scraper SHALL occasionally go back to previous pages (simulate back button) 
5. THE Scraper SHALL limit total scraping duration per session to a configurable maximum (e.g., 2 hours) before requiring a break
6. THE Scraper SHALL implement session breaks: after N minutes of scraping, pause for M minutes before resuming
7. WHEN resuming after a break, THE Session_Manager SHALL optionally create a new session with new fingerprint

### Requirement 19: Headless Browser Emulation

**User Story:** As a developer, I want to use headless browser technology, so that JavaScript-rendered content is accessible and bot detection is nearly impossible.

#### Acceptance Criteria

1. THE Scraper SHALL support Playwright or Puppeteer for browser automation (configurable)
2. THE Browser_Engine SHALL use stealth plugins to hide automation indicators (navigator.webdriver, chrome.runtime, etc.)
3. THE Browser_Engine SHALL execute JavaScript and wait for dynamic content to load before extracting data
4. THE Browser_Engine SHALL simulate realistic mouse movements and scrolling behavior
5. WHEN using headless mode, THE Browser_Engine SHALL randomize canvas fingerprints to avoid canvas fingerprinting detection
6. THE Browser_Engine SHALL randomize WebGL fingerprints to avoid WebGL fingerprinting detection
7. THE Browser_Engine SHALL randomize audio context fingerprints to avoid audio fingerprinting detection
8. THE Browser_Engine SHALL block or randomize font fingerprinting attempts
9. THE Browser_Engine SHALL simulate realistic viewport scrolling (smooth scroll, random scroll depth)
10. WHEN a page requires interaction, THE Browser_Engine SHALL simulate human-like mouse movements using Bezier curves
11. THE Browser_Engine SHALL support running in headed mode (visible browser) for debugging purposes

### Requirement 20: CAPTCHA Detection and Handling

**User Story:** As a developer, I want to detect and handle CAPTCHAs, so that scraping can continue even when anti-bot measures are triggered.

#### Acceptance Criteria

1. WHEN a CAPTCHA is detected on a page, THE Scraper SHALL log a CAPTCHA detection event with the page URL
2. THE Scraper SHALL support manual CAPTCHA solving: pause execution and wait for user input
3. THE Scraper SHALL support automatic CAPTCHA solving via 2Captcha or Anti-Captcha service integration (configurable)
4. WHEN CAPTCHA solving fails after 3 attempts, THE Scraper SHALL skip the current page and continue with the next
5. THE Scraper SHALL detect common CAPTCHA types: reCAPTCHA v2, reCAPTCHA v3, hCaptcha, image CAPTCHA, Tokopedia custom puzzle CAPTCHA
6. WHEN a CAPTCHA is solved successfully, THE Scraper SHALL save the session cookies for reuse
7. THE Scraper SHALL implement exponential backoff after CAPTCHA encounters (wait longer before next request)

### Requirement 27: Tokopedia Custom CAPTCHA Puzzle Handling

**User Story:** As a developer, I want to handle Tokopedia's custom puzzle CAPTCHA that appears on affiliator detail pages, so that scraping can continue automatically without manual intervention.

#### Acceptance Criteria

1. WHEN navigating to an affiliator detail page in a new tab, THE Scraper SHALL detect if a Tokopedia custom puzzle CAPTCHA is present
2. WHEN a Tokopedia puzzle CAPTCHA is detected, THE Scraper SHALL automatically refresh the page once to bypass the puzzle
3. AFTER refreshing the page, THE Scraper SHALL verify that the actual profile data is now visible and the puzzle has disappeared
4. WHEN the puzzle persists after one refresh, THE Scraper SHALL attempt up to 2 additional refreshes before marking the page as failed
5. THE Scraper SHALL distinguish Tokopedia's custom puzzle CAPTCHA from standard CAPTCHAs (reCAPTCHA, hCaptcha) by detecting puzzle-specific elements or page patterns
6. WHEN opening detail pages, THE Scraper SHALL open them in new tabs to mimic natural user behavior that triggers the puzzle pattern
7. THE Scraper SHALL implement a wait period of 2-3 seconds after page load before checking for puzzle presence to allow dynamic content to render
8. WHEN a puzzle is successfully bypassed, THE Scraper SHALL log the successful bypass and continue with data extraction
9. THE Scraper SHALL track puzzle encounter rate and log warnings if the rate exceeds 50% to indicate potential detection
10. WHEN multiple consecutive pages show puzzles (5+ in a row), THE Scraper SHALL pause for 5-10 minutes before continuing to avoid triggering enhanced anti-bot measures

### Requirement 21: Behavioral Biometrics Simulation

**User Story:** As a developer, I want to simulate human behavioral biometrics, so that advanced bot detection systems cannot distinguish the scraper from real users.

#### Acceptance Criteria

1. THE Browser_Engine SHALL simulate realistic typing speed (200-400ms per character with random variations) when filling forms
2. THE Browser_Engine SHALL simulate realistic mouse movement patterns (curved paths, acceleration/deceleration)
3. THE Browser_Engine SHALL simulate random mouse movements even when not clicking (idle mouse movement)
4. THE Browser_Engine SHALL simulate realistic scroll patterns (variable speed, occasional scroll-up, pauses)
5. THE Browser_Engine SHALL randomize click positions within clickable elements (not always center)
6. THE Browser_Engine SHALL simulate occasional misclicks (click near but not on target, then correct)
7. THE Browser_Engine SHALL implement random page interactions: hover over elements, scroll to random positions
8. THE Scraper SHALL vary interaction patterns between sessions (different scroll depths, different hover targets)

### Requirement 22: TLS Fingerprint Randomization

**User Story:** As a developer, I want to randomize TLS fingerprints, so that the scraper cannot be identified by TLS/SSL handshake patterns.

#### Acceptance Criteria

1. THE HTTP_Client SHALL use libraries that support TLS fingerprint randomization (e.g., curl-impersonate, tls-client)
2. THE HTTP_Client SHALL mimic TLS fingerprints of real browsers (Chrome, Firefox, Safari)
3. THE HTTP_Client SHALL randomize cipher suites to match the selected browser fingerprint
4. THE HTTP_Client SHALL use HTTP/2 with realistic SETTINGS frames matching real browsers
5. THE HTTP_Client SHALL randomize the order of TLS extensions to match real browser behavior
6. WHEN using headless browser mode, THE Browser_Engine SHALL automatically handle TLS fingerprinting

### Requirement 23: Cookie and Storage Management

**User Story:** As a developer, I want to manage cookies and local storage realistically, so that session persistence appears natural.

#### Acceptance Criteria

1. THE Session_Manager SHALL accept and store all cookies sent by the server
2. THE Session_Manager SHALL implement realistic cookie expiration handling
3. THE Browser_Engine SHALL support localStorage and sessionStorage persistence across page navigations
4. THE Session_Manager SHALL clear cookies and storage when starting a new session with new fingerprint
5. THE Session_Manager SHALL support importing real browser cookies for authenticated scraping
6. WHEN cookies indicate session expiration, THE Session_Manager SHALL attempt to refresh the session or create a new one
7. THE Session_Manager SHALL respect cookie domain and path restrictions

### Requirement 24: Traffic Volume Control

**User Story:** As a developer, I want to control scraping volume, so that traffic patterns do not trigger anomaly detection systems.

#### Acceptance Criteria

1. THE Scraper SHALL support configurable daily request limits (e.g., max 500 requests per day)
2. THE Scraper SHALL support configurable hourly request limits (e.g., max 50 requests per hour)
3. WHEN a limit is reached, THE Scraper SHALL pause until the limit window resets
4. THE Scraper SHALL distribute requests evenly across the time window (avoid bursts)
5. THE Scraper SHALL support configurable "quiet hours" where scraping is paused (e.g., 1 AM - 6 AM)
6. THE Scraper SHALL maintain a request log with timestamps for rate limit enforcement
7. THE Scraper SHALL support resuming from the last scraped position after hitting rate limits

### Requirement 25: Error Response Analysis

**User Story:** As a developer, I want to analyze error responses, so that I can detect when anti-bot measures are triggered and adjust behavior accordingly.

#### Acceptance Criteria

1. WHEN receiving a 403 Forbidden response, THE Scraper SHALL log it as a potential bot detection event
2. WHEN receiving a 429 Too Many Requests response, THE Scraper SHALL increase delay times by 50% for subsequent requests
3. WHEN receiving multiple 403/429 responses in a row (3+), THE Scraper SHALL pause for 5-15 minutes before resuming
4. THE Scraper SHALL detect redirect loops (potential bot trap) and abort after 3 redirects to the same URL
5. THE Scraper SHALL detect honeypot links (hidden links in HTML) and avoid following them
6. WHEN response times suddenly increase significantly, THE Scraper SHALL interpret it as potential rate limiting and slow down
7. THE Scraper SHALL detect JavaScript challenges (Cloudflare, etc.) and handle them using the browser engine
8. WHEN a page returns empty or minimal content, THE Scraper SHALL retry with browser engine instead of HTTP client

### Requirement 26: Distributed Scraping Support

**User Story:** As a developer, I want to distribute scraping across multiple machines/IPs, so that no single IP generates suspicious traffic volume.

#### Acceptance Criteria

1. THE Scraper SHALL support work queue distribution: multiple scraper instances can pull from a shared queue
2. THE Scraper SHALL support result aggregation: multiple instances can write to a shared data store
3. THE Scraper SHALL implement distributed locking to prevent duplicate scraping of the same affiliator
4. THE Scraper SHALL support coordination via Redis or similar distributed cache
5. WHEN running in distributed mode, EACH instance SHALL maintain its own rate limits independently
6. THE Scraper SHALL support splitting the affiliator list across multiple instances by ID ranges or hash partitioning
7. THE Scraper SHALL handle instance failures gracefully: incomplete work is returned to the queue for retry
