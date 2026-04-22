"""Configuration models for the scraper"""

from dataclasses import dataclass, field
from typing import List, Tuple, Optional
import json
from pathlib import Path


@dataclass
class ProxyConfig:
    """Proxy configuration"""
    protocol: str  # http, https, socks5
    host: str
    port: int
    username: Optional[str] = None
    password: Optional[str] = None
    
    def to_url(self) -> str:
        """Convert to proxy URL string"""
        if self.username and self.password:
            return f"{self.protocol}://{self.username}:{self.password}@{self.host}:{self.port}"
        return f"{self.protocol}://{self.host}:{self.port}"
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "protocol": self.protocol,
            "host": self.host,
            "port": self.port,
            "username": self.username,
            "password": self.password
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "ProxyConfig":
        """Create from dictionary"""
        return cls(
            protocol=data["protocol"],
            host=data["host"],
            port=data["port"],
            username=data.get("username"),
            password=data.get("password")
        )


@dataclass
class Configuration:
    """Scraper configuration"""
    # URLs
    base_url: str = "https://affiliate-id.tokopedia.com"
    list_page_url: str = "/connection/creator"
    list_page_query: str = ""
    
    # Rate limiting
    min_delay: float = 2.0
    max_delay: float = 5.0
    jitter: float = 0.2
    
    # Traffic control
    hourly_limit: int = 50
    daily_limit: int = 500
    max_session_duration: int = 7200  # 2 hours in seconds
    break_duration_min: int = 900  # 15 minutes
    break_duration_max: int = 1800  # 30 minutes
    quiet_hours: List[Tuple[int, int]] = field(default_factory=lambda: [(1, 6)])  # 1 AM - 6 AM
    
    # Request settings
    request_timeout: int = 30
    max_retries: int = 3
    max_redirects: int = 5
    
    # Browser settings
    browser_engine: str = "playwright"  # or "puppeteer"
    headless: bool = True
    use_stealth: bool = True
    
    # Proxy settings
    proxies: List[ProxyConfig] = field(default_factory=list)
    proxy_rotation_strategy: str = "per_session"  # per_request, per_session, per_n_requests
    proxy_rotation_interval: int = 10  # for per_n_requests strategy
    
    # CAPTCHA settings
    captcha_solver: str = "manual"  # manual, 2captcha, anticaptcha
    captcha_api_key: Optional[str] = None
    
    # Output settings
    output_format: str = "json"  # json, csv, or xlsx
    output_path: str = "output/affiliators.json"
    # Session/cookie settings
    cookie_file: Optional[str] = None
    require_cookie_file: bool = False

    incremental_save: bool = True
    save_interval: int = 10  # save every N affiliators
    max_pages_per_run: int = 50
    max_errors_before_stop: int = 20
    max_captchas_before_stop: int = 5
    
    # Logging
    log_level: str = "INFO"
    log_file: str = "logs/scraper.log"
    
    # Distributed mode
    distributed: bool = False
    redis_url: Optional[str] = None
    instance_id: Optional[str] = None
    
    @classmethod
    def from_file(cls, filepath: str) -> "Configuration":
        """Load configuration from JSON file"""
        path = Path(filepath)
        
        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {filepath}")
        
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Convert proxy configs
        if "proxies" in data and data["proxies"]:
            data["proxies"] = [ProxyConfig.from_dict(p) for p in data["proxies"]]
        
        # Convert quiet_hours to list of tuples
        if "quiet_hours" in data and data["quiet_hours"]:
            data["quiet_hours"] = [tuple(qh) for qh in data["quiet_hours"]]
        
        return cls(**data)
    
    def validate(self) -> List[str]:
        """Validate configuration and return list of errors"""
        errors = []
        
        # Validate URLs
        if not self.base_url:
            errors.append("base_url cannot be empty")
        if not self.base_url.startswith(("http://", "https://")):
            errors.append("base_url must start with http:// or https://")
        
        # Validate rate limiting
        if self.min_delay < 0:
            errors.append("min_delay must be non-negative")
        if self.max_delay < self.min_delay:
            errors.append("max_delay must be greater than or equal to min_delay")
        if not 0 <= self.jitter <= 1:
            errors.append("jitter must be between 0 and 1")
        
        # Validate traffic control
        if self.hourly_limit <= 0:
            errors.append("hourly_limit must be positive")
        if self.daily_limit <= 0:
            errors.append("daily_limit must be positive")
        if self.max_session_duration <= 0:
            errors.append("max_session_duration must be positive")
        if self.break_duration_min < 0:
            errors.append("break_duration_min must be non-negative")
        if self.break_duration_max < self.break_duration_min:
            errors.append("break_duration_max must be greater than or equal to break_duration_min")
        
        # Validate quiet hours
        for start, end in self.quiet_hours:
            if not (0 <= start < 24):
                errors.append(f"quiet_hours start hour {start} must be between 0 and 23")
            if not (0 <= end < 24):
                errors.append(f"quiet_hours end hour {end} must be between 0 and 23")
        
        # Validate request settings
        if self.request_timeout <= 0:
            errors.append("request_timeout must be positive")
        if self.max_retries < 0:
            errors.append("max_retries must be non-negative")
        if self.max_redirects < 0:
            errors.append("max_redirects must be non-negative")
        
        # Validate browser settings
        if self.browser_engine not in ["playwright", "puppeteer"]:
            errors.append("browser_engine must be 'playwright' or 'puppeteer'")
        
        # Validate proxy settings
        if self.proxy_rotation_strategy not in ["per_request", "per_session", "per_n_requests", "round_robin", "random", "least_used"]:
            errors.append(f"Invalid proxy_rotation_strategy: {self.proxy_rotation_strategy}")
        if self.proxy_rotation_interval <= 0:
            errors.append("proxy_rotation_interval must be positive")
        
        # Validate CAPTCHA settings
        if self.captcha_solver not in ["manual", "2captcha", "anticaptcha"]:
            errors.append(f"Invalid captcha_solver: {self.captcha_solver}")
        if self.captcha_solver in ["2captcha", "anticaptcha"] and not self.captcha_api_key:
            errors.append(f"captcha_api_key is required when using {self.captcha_solver}")
        
        # Validate output settings
        if self.output_format not in ["json", "csv", "xlsx"]:
            errors.append(f"Invalid output_format: {self.output_format}")
        if not self.output_path:
            errors.append("output_path cannot be empty")
        if self.save_interval <= 0:
            errors.append("save_interval must be positive")
        if self.max_pages_per_run <= 0:
            errors.append("max_pages_per_run must be positive")
        if self.max_errors_before_stop <= 0:
            errors.append("max_errors_before_stop must be positive")
        if self.max_captchas_before_stop <= 0:
            errors.append("max_captchas_before_stop must be positive")
        if self.require_cookie_file and not self.cookie_file:
            errors.append("cookie_file is required when require_cookie_file is enabled")
        
        # Validate logging
        if self.log_level not in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            errors.append(f"Invalid log_level: {self.log_level}")
        if not self.log_file:
            errors.append("log_file cannot be empty")
        
        # Validate distributed mode
        if self.distributed and not self.redis_url:
            errors.append("redis_url is required when distributed mode is enabled")
        
        return errors
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "base_url": self.base_url,
            "list_page_url": self.list_page_url,
            "list_page_query": self.list_page_query,
            "min_delay": self.min_delay,
            "max_delay": self.max_delay,
            "jitter": self.jitter,
            "hourly_limit": self.hourly_limit,
            "daily_limit": self.daily_limit,
            "max_session_duration": self.max_session_duration,
            "break_duration_min": self.break_duration_min,
            "break_duration_max": self.break_duration_max,
            "quiet_hours": self.quiet_hours,
            "request_timeout": self.request_timeout,
            "max_retries": self.max_retries,
            "max_redirects": self.max_redirects,
            "browser_engine": self.browser_engine,
            "headless": self.headless,
            "use_stealth": self.use_stealth,
            "proxies": [p.to_dict() for p in self.proxies],
            "proxy_rotation_strategy": self.proxy_rotation_strategy,
            "proxy_rotation_interval": self.proxy_rotation_interval,
            "captcha_solver": self.captcha_solver,
            "captcha_api_key": self.captcha_api_key,
            "output_format": self.output_format,
            "output_path": self.output_path,
            "incremental_save": self.incremental_save,
            "save_interval": self.save_interval,
            "cookie_file": self.cookie_file,
            "require_cookie_file": self.require_cookie_file,
            "max_pages_per_run": self.max_pages_per_run,
            "max_errors_before_stop": self.max_errors_before_stop,
            "max_captchas_before_stop": self.max_captchas_before_stop,
            "log_level": self.log_level,
            "log_file": self.log_file,
            "distributed": self.distributed,
            "redis_url": self.redis_url,
            "instance_id": self.instance_id
        }
