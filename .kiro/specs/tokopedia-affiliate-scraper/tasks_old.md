# Implementation Tasks

## Phase 1: Core Infrastructure

### Task 1: Project Setup and Configuration Management
- [x] 1.1 Create project structure (src/, tests/, config/, logs/, output/)
- [x] 1.2 Create requirements.txt with core dependencies (requests, lxml, beautifulsoup4)
- [x] 1.3 Implement Configuration dataclass with simplified fields
  - Remove browser/stealth/CAPTCHA settings
  - Add cookie_file setting
  - Keep rate limiting, traffic control, proxy settings
  - _Requirements: 11.1, 11.2_
- [x] 1.4 Implement Configuration.from_file() to load JSON config
  - _Requirements: 11.1_
- [x] 1.5 Implement Configuration.validate() with validation rules
  - _Requirements: 11.4, 11.5_
- [x] 1.6 Create default config.json template with cookie_file path
  - _Requirements: 11.3_
- [x] 1.7 Write unit tests for configuration loading and validation
  - _Requirements: 11.1, 11.4, 11.5_

### Task 2: Data Models
- [x] 2.1 Implement AffiliatorData dataclass
  - _Requirements: 4.2, 5.2_
- [x] 2.2 Remove BrowserFingerprint dataclass (not needed)
- [x] 2.3 Implement ProxyConfig dataclass
  - _Requirements: 16.1, 16.2_
- [x] 2.4 Implement ScrapingResult dataclass
  - _Requirements: 10.4_
- [x] 2.5 Implement Checkpoint dataclass with save/load methods
  - _Requirements: 10.7, 10.8_
- [x] 2.6 Implement to_dict() and from_dict() methods for all models
  - _Requirements: 7.1, 7.2_
- [x] 2.7 Write unit tests for all data models

### Task 3: HTTP Client (Simplified)
- [x] 3.1 Implement HTTPClient class with requests library
  - Remove TLS fingerprinting
  - Use simple requests.Session
  - _Requirements: 1.1_
- [x] 3.2 Implement GET and POST methods with cookies
  - _Requirements: 1.1, 1.5_
- [x] 3.3 Implement cookie loading from file
  - Load from config/cookies.json
  - _Requirements: 8.4_
- [x] 3.4 Implement retry logic with exponential backoff
  - _Requirements: 1.2_
- [x] 3.5 Implement timeout handling (30 seconds)
  - _Requirements: 1.6_
- [x] 3.6 Implement redirect following (max 5 hops)
  - _Requirements: 14.5_
- [x] 3.7 Implement realistic browser headers (User-Agent, Accept, Referer)
  - _Requirements: 1.4, 14.2, 14.6_
- [x] 3.8 Write unit and integration tests for HTTP client
  - _Requirements: 1.1, 1.2, 1.4, 1.5_

### Task 4: HTML Parser
- [x] 4.1 Implement HTMLParser class with lxml
  - _Requirements: 3.1_
- [x] 4.2 Implement parse() method for HTML to DOM
  - _Requirements: 3.1_
- [x] 4.3 Implement select() method for CSS selectors
  - _Requirements: 3.3_
- [x] 4.4 Implement xpath() method for XPath queries
  - _Requirements: 3.4_
- [x] 4.5 Implement get_text() with whitespace normalization
  - _Requirements: 13.4_
- [x] 4.6 Implement get_attribute() method
- [x] 4.7 Add error recovery for malformed HTML (html5lib fallback)
  - _Requirements: 3.2_
- [x] 4.8 Write unit tests with sample HTML
  - _Requirements: 3.1, 3.2, 3.3, 3.4_

## Phase 2: Manual Cookie Extraction & Validation

### Task 5: Cookie Extraction Guide
- [ ] 5.1 Implement CookieExtractionGuide class
  - Interactive CLI guide for users
  - _Requirements: 8.4_
- [ ] 5.2 Implement show_guide() method
  - Display step-by-step instructions
  - Show Chrome DevTools navigation
  - Explain cookie export process
- [ ] 5.3 Create example cookies.json template
  - Document required cookie format
  - Include domain, path, httpOnly, secure fields
- [ ] 5.4 Write guide documentation in README
  - Screenshots of DevTools
  - Step-by-step cookie extraction
  - Troubleshooting common issues

### Task 6: Cookie Validator
- [ ] 6.1 Implement CookieValidator class
  - _Requirements: 8.4_
- [ ] 6.2 Implement validate_format() method
  - Check JSON structure
  - Validate required fields (name, value, domain)
  - Verify domain matches Tokopedia
- [ ] 6.3 Implement check_expiration() method
  - Parse expiration timestamps
  - Warn if cookies expire soon
- [ ] 6.4 Implement test_cookies() method
  - Make test request to Tokopedia affiliate page
  - Verify 200 response (not redirect to login)
  - Detect "Coba lagi" blocking page
  - _Requirements: 1.1, 8.6_
- [ ] 6.5 Write unit tests for cookie validation
  - Test valid cookie formats
  - Test invalid formats
  - Test expired cookies

## Phase 3: Data Extraction

### Task 7: Affiliator Extractor
- [x] 7.1 Create selector configuration file for Tokopedia pages
  - _Requirements: 13.1_
- [x] 7.2 Implement AffiliatorExtractor class
- [x] 7.3 Implement extract_list_page() method
  - _Requirements: 4.1, 4.2_
- [x] 7.4 Implement extract_detail_page() method
  - _Requirements: 5.1, 5.2_
- [x] 7.5 Implement extract_next_page_url() method
  - _Requirements: 4.5, 4.6_
- [x] 7.6 Implement fallback selector mechanism
  - _Requirements: 13.1, 13.2, 13.3_
- [x] 7.7 Implement numeric parsing with formatting (1,234, 1.2K, 1.5M)
  - _Requirements: 13.5_
- [x] 7.8 Write unit tests with real Tokopedia HTML samples
  - _Requirements: 4.1, 4.2, 5.1, 5.2_

### Task 8: Contact Extractor (WhatsApp & Email)
- [ ] 8.1 Implement ContactExtractor class
  - Specialized for extracting contact information
  - _Requirements: 5.2, 5.3_
- [ ] 8.2 Implement extract_whatsapp() method
  - Multiple selector fallbacks
  - Parse WhatsApp number format
  - Handle Indonesian phone formats (08xxx, +62xxx)
  - _Requirements: 5.2, 6.4_
- [ ] 8.3 Implement extract_email() method
  - Multiple selector fallbacks
  - Validate email format
  - _Requirements: 5.2_
- [ ] 8.4 Integrate ContactExtractor into AffiliatorExtractor
  - Call from extract_detail_page()
  - _Requirements: 5.2_
- [ ] 8.5 Write unit tests with real contact data samples
  - Test WhatsApp extraction
  - Test email extraction
  - Test missing contact scenarios

### Task 9: Data Validation
- [x] 9.1 Implement DataValidator class
  - _Requirements: 6.1, 6.2, 6.3, 6.4_
- [x] 9.2 Implement username validation (non-empty string)
  - _Requirements: 6.1_
- [x] 9.3 Implement numeric field validation and conversion
  - _Requirements: 6.2_
- [x] 9.4 Implement percentage validation (0-100)
  - _Requirements: 6.3_
- [x] 9.5 Implement Indonesian phone number validation (regex)
  - _Requirements: 6.4_
- [x] 9.6 Implement validate() method returning ValidationResult
  - _Requirements: 6.5_
- [x] 9.7 Write unit and property-based tests for validation
  - _Requirements: 6.1, 6.2, 6.3, 6.4_

### Task 10: Data Store
- [x] 10.1 Implement DataStore class
  - _Requirements: 7.1, 7.2_
- [x] 10.2 Implement JSON serialization (save, load)
  - _Requirements: 7.1, 7.3_
- [x] 10.3 Implement CSV serialization (save, load)
  - _Requirements: 7.2, 7.4_
- [x] 10.4 Implement incremental save (append mode)
  - _Requirements: 7.5_
- [x] 10.5 Implement special character escaping for CSV
  - _Requirements: 7.4_
- [x] 10.6 Implement file I/O error handling
  - _Requirements: 7.6_
- [x] 10.7 Write unit and property-based tests for serialization
  - _Requirements: 7.1, 7.2, 7.3, 7.4, 12.1, 12.2, 12.3, 12.4_

## Phase 4: Control Systems

### Task 11: Rate Limiter
- [x] 11.1 Implement RateLimiter class
  - _Requirements: 2.1, 2.2_
- [x] 11.2 Implement wait() method with jitter
  - _Requirements: 2.1, 14.4_
- [x] 11.3 Implement random delay between min_delay and max_delay
  - _Requirements: 2.1, 14.9_
- [x] 11.4 Implement adjust_delay() for dynamic adjustment
  - _Requirements: 25.2_
- [x] 11.5 Implement reset() method
- [x] 11.6 Write unit and property-based tests for rate limiting
  - _Requirements: 2.1, 2.2, 2.4_

### Task 12: Traffic Controller
- [x] 12.1 Implement TrafficController class
  - _Requirements: 24.1, 24.2_
- [x] 12.2 Implement hourly request limit tracking
  - _Requirements: 24.1_
- [x] 12.3 Implement daily request limit tracking
  - _Requirements: 24.2_
- [x] 12.4 Implement check_permission() method
  - _Requirements: 24.3_
- [x] 12.5 Implement wait_for_window_reset() method
  - _Requirements: 24.3_
- [x] 12.6 Implement session break logic (should_take_break, take_break)
  - _Requirements: 18.6_
- [x] 12.7 Implement quiet hours enforcement
  - _Requirements: 24.5_
- [x] 12.8 Implement request log with timestamps
  - _Requirements: 24.6_
- [x] 12.9 Write unit tests for traffic control
  - _Requirements: 24.1, 24.2, 24.3_

### Task 13: Session Manager (Simplified)
- [x] 13.1 Implement SessionManager class
  - Remove localStorage/sessionStorage (not needed for HTTP)
  - _Requirements: 8.1_
- [x] 13.2 Implement load_cookies() from file
  - _Requirements: 8.4_
- [x] 13.3 Implement save_cookies() to file
  - _Requirements: 8.5_
- [x] 13.4 Implement is_expired() detection
  - Check for redirect to login
  - Detect "Coba lagi" page
  - _Requirements: 8.6_
- [x] 13.5 Write unit and property-based tests for session management
  - _Requirements: 8.2, 8.3, 8.4, 8.5_

### Task 14: Proxy Rotator (Optional)
- [x] 14.1 Implement ProxyRotator class
  - _Requirements: 16.1, 16.2, 16.3_
- [x] 14.2 Implement proxy pool management
  - _Requirements: 16.3_
- [x] 14.3 Implement rotation strategies (per_request, per_session, per_n_requests, round_robin, random, least_used)
  - _Requirements: 16.6_
- [x] 14.4 Implement proxy health tracking (success/failure counts)
  - _Requirements: 16.4_
- [x] 14.5 Implement mark_failed() and mark_success() methods
  - _Requirements: 16.4_
- [x] 14.6 Implement validate_proxy() method
  - _Requirements: 16.8_
- [x] 14.7 Implement get_next_proxy() with strategy selection
  - _Requirements: 16.3, 16.6_
- [x] 14.8 Write unit tests for proxy rotation
  - _Requirements: 16.3, 16.4, 16.6_

## Phase 5: Error Handling

### Task 15: Error Analyzer (Enhanced)
- [x] 15.1 Implement ErrorAnalyzer class
  - _Requirements: 25.1, 25.2, 25.3_
- [x] 15.2 Implement analyze() method for response analysis
  - _Requirements: 25.1, 25.2_
- [x] 15.3 Implement 403 Forbidden detection and handling
  - _Requirements: 25.1_
- [x] 15.4 Implement 429 Too Many Requests detection and handling
  - _Requirements: 25.2_
- [x] 15.5 Implement redirect loop detection
  - _Requirements: 25.4_
- [x] 15.6 Implement honeypot link detection
  - _Requirements: 25.5_
- [x] 15.7 Implement response time analysis
  - _Requirements: 25.6_
- [ ] 15.8 Implement detect_coba_lagi() method
  - Detect "Coba lagi" blocking page
  - Check for specific text or page structure
  - _Requirements: 8.6, 25.1_
- [ ] 15.9 Implement detect_cookie_expiration() method
  - Detect redirect to login page
  - Detect session expired messages
  - _Requirements: 8.6_
- [x] 15.10 Implement should_slow_down() and should_pause() methods
  - _Requirements: 25.2, 25.3_
- [x] 15.11 Implement get_recommended_action() method
  - _Requirements: 25.1, 25.2, 25.3_
- [ ] 15.12 Write unit tests for error analysis
  - Test "Coba lagi" detection
  - Test cookie expiration detection
  - _Requirements: 25.1, 25.2, 25.3_

### Task 16: Logging System
- [x] 16.1 Setup structlog for structured logging
  - _Requirements: 9.1, 9.2_
- [x] 16.2 Implement log configuration (levels, formats)
  - _Requirements: 9.5_
- [x] 16.3 Implement console logging
  - _Requirements: 9.2_
- [x] 16.4 Implement file logging with rotation
  - _Requirements: 9.6_
- [x] 16.5 Implement error context capture
  - _Requirements: 9.1_
- [x] 16.6 Implement progress logging
  - _Requirements: 9.3, 10.5_
- [x] 16.7 Write unit tests for logging
  - _Requirements: 9.1, 9.2_

## Phase 6: Orchestration

### Task 17: Deduplicator
- [x] 17.1 Implement Deduplicator class
  - _Requirements: 15.1, 15.2_
- [x] 17.2 Implement username-based deduplication
  - _Requirements: 15.1, 15.2_
- [x] 17.3 Implement duplicate detection (is_duplicate method)
  - _Requirements: 15.2_
- [x] 17.4 Implement duplicate counting
  - _Requirements: 15.4_
- [x] 17.5 Implement add() method with deduplication
  - _Requirements: 15.1_
- [x] 17.6 Write unit and property-based tests for deduplication
  - _Requirements: 15.1, 15.2, 15.4_

### Task 18: Scraper Orchestrator (Simplified for HTTP)
- [x] 18.1 Implement ScraperOrchestrator class
  - Remove browser initialization
  - Add cookie loading/validation
  - _Requirements: 10.1, 10.2_
- [ ] 18.2 Implement __init__() with component initialization
  - Initialize HTTP client with cookies
  - Initialize all control components
  - _Requirements: 10.1_
- [ ] 18.3 Implement cookie validation at startup
  - Load cookies from file
  - Validate format and expiration
  - Test cookies with request
  - Exit with error if cookies invalid
  - _Requirements: 8.4, 8.6_
- [x] 18.4 Implement start() method - main scraping loop
  - _Requirements: 10.1, 10.2_
- [x] 18.5 Implement list page iteration with pagination
  - _Requirements: 10.1, 4.5, 4.6_
- [x] 18.6 Implement detail page scraping for each affiliator
  - Use HTTP GET with cookies (no browser)
  - _Requirements: 10.2, 5.1_
- [x] 18.7 Implement progress reporting
  - _Requirements: 10.5_
- [x] 18.8 Implement checkpoint saving (periodic)
  - _Requirements: 10.7_
- [x] 18.9 Implement resume() method from checkpoint
  - _Requirements: 10.8_
- [x] 18.10 Implement stop() method for graceful shutdown
  - _Requirements: 10.9_
- [x] 18.11 Implement SIGINT handler for partial save
  - _Requirements: 10.10_
- [ ] 18.12 Implement cookie expiration handling
  - Detect expired cookies during scraping
  - Prompt user to refresh cookies
  - Pause until new cookies provided
  - _Requirements: 8.6_
- [ ] 18.13 Write integration and E2E tests for orchestrator
  - _Requirements: 10.1, 10.2, 10.3, 10.4_
