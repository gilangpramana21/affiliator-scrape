"""Unit tests for Configuration class"""

import json
import pytest
from pathlib import Path
from src.models.config import Configuration, ProxyConfig


class TestConfigurationFromFile:
    """Tests for Configuration.from_file() method"""
    
    def test_load_valid_config(self, tmp_path):
        """Test loading a valid configuration file"""
        config_data = {
            "base_url": "https://example.com",
            "min_delay": 3.0,
            "max_delay": 6.0,
            "output_format": "csv"
        }
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(config_data))
        
        config = Configuration.from_file(str(config_file))
        
        assert config.base_url == "https://example.com"
        assert config.min_delay == 3.0
        assert config.max_delay == 6.0
        assert config.output_format == "csv"
    
    def test_load_config_with_defaults(self, tmp_path):
        """Test that unspecified fields use default values"""
        config_data = {"base_url": "https://example.com"}
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(config_data))
        
        config = Configuration.from_file(str(config_file))
        
        assert config.base_url == "https://example.com"
        assert config.min_delay == 2.0  # default
        assert config.max_delay == 5.0  # default
        assert config.output_format == "json"  # default
    
    def test_load_config_with_proxies(self, tmp_path):
        """Test loading configuration with proxy list"""
        config_data = {
            "proxies": [
                {
                    "protocol": "http",
                    "host": "proxy1.example.com",
                    "port": 8080,
                    "username": "user1",
                    "password": "pass1"
                },
                {
                    "protocol": "socks5",
                    "host": "proxy2.example.com",
                    "port": 1080
                }
            ]
        }
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(config_data))
        
        config = Configuration.from_file(str(config_file))
        
        assert len(config.proxies) == 2
        assert isinstance(config.proxies[0], ProxyConfig)
        assert config.proxies[0].protocol == "http"
        assert config.proxies[0].host == "proxy1.example.com"
        assert config.proxies[0].port == 8080
        assert config.proxies[0].username == "user1"
        assert config.proxies[0].password == "pass1"
        assert config.proxies[1].protocol == "socks5"
        assert config.proxies[1].username is None
    
    def test_load_config_with_quiet_hours(self, tmp_path):
        """Test loading configuration with quiet hours"""
        config_data = {
            "quiet_hours": [[1, 6], [13, 14]]
        }
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(config_data))
        
        config = Configuration.from_file(str(config_file))
        
        assert len(config.quiet_hours) == 2
        assert config.quiet_hours[0] == (1, 6)
        assert config.quiet_hours[1] == (13, 14)
    
    def test_missing_config_file(self):
        """Test that FileNotFoundError is raised for missing file"""
        with pytest.raises(FileNotFoundError) as exc_info:
            Configuration.from_file("nonexistent.json")
        
        assert "Configuration file not found" in str(exc_info.value)
        assert "nonexistent.json" in str(exc_info.value)
    
    def test_invalid_json_format(self, tmp_path):
        """Test handling of invalid JSON format"""
        config_file = tmp_path / "invalid.json"
        config_file.write_text("{ invalid json }")
        
        with pytest.raises(json.JSONDecodeError):
            Configuration.from_file(str(config_file))
    
    def test_empty_json_file(self, tmp_path):
        """Test loading empty JSON object (all defaults)"""
        config_file = tmp_path / "empty.json"
        config_file.write_text("{}")
        
        config = Configuration.from_file(str(config_file))
        
        # Should use all default values
        assert config.base_url == "https://affiliate-id.tokopedia.com"
        assert config.min_delay == 2.0
        assert config.output_format == "json"


class TestConfigurationValidation:
    """Tests for Configuration.validate() method"""
    
    def test_valid_configuration(self):
        """Test that valid configuration passes validation"""
        config = Configuration()
        errors = config.validate()
        
        assert errors == []
    
    def test_empty_base_url(self):
        """Test validation error for empty base_url"""
        config = Configuration(base_url="")
        errors = config.validate()
        
        assert "base_url cannot be empty" in errors
    
    def test_invalid_base_url_protocol(self):
        """Test validation error for invalid URL protocol"""
        config = Configuration(base_url="ftp://example.com")
        errors = config.validate()
        
        assert any("base_url must start with http://" in e for e in errors)
    
    def test_negative_min_delay(self):
        """Test validation error for negative min_delay"""
        config = Configuration(min_delay=-1.0)
        errors = config.validate()
        
        assert "min_delay must be non-negative" in errors
    
    def test_max_delay_less_than_min_delay(self):
        """Test validation error when max_delay < min_delay"""
        config = Configuration(min_delay=5.0, max_delay=3.0)
        errors = config.validate()
        
        assert any("max_delay must be greater than or equal to min_delay" in e for e in errors)
    
    def test_jitter_out_of_range(self):
        """Test validation error for jitter outside [0, 1]"""
        config = Configuration(jitter=1.5)
        errors = config.validate()
        
        assert "jitter must be between 0 and 1" in errors
        
        config = Configuration(jitter=-0.1)
        errors = config.validate()
        
        assert "jitter must be between 0 and 1" in errors
    
    def test_negative_hourly_limit(self):
        """Test validation error for non-positive hourly_limit"""
        config = Configuration(hourly_limit=0)
        errors = config.validate()
        
        assert "hourly_limit must be positive" in errors
    
    def test_negative_daily_limit(self):
        """Test validation error for non-positive daily_limit"""
        config = Configuration(daily_limit=-10)
        errors = config.validate()
        
        assert "daily_limit must be positive" in errors
    
    def test_negative_max_session_duration(self):
        """Test validation error for non-positive max_session_duration"""
        config = Configuration(max_session_duration=0)
        errors = config.validate()
        
        assert "max_session_duration must be positive" in errors
    
    def test_negative_break_duration_min(self):
        """Test validation error for negative break_duration_min"""
        config = Configuration(break_duration_min=-100)
        errors = config.validate()
        
        assert "break_duration_min must be non-negative" in errors
    
    def test_break_duration_max_less_than_min(self):
        """Test validation error when break_duration_max < break_duration_min"""
        config = Configuration(break_duration_min=1800, break_duration_max=900)
        errors = config.validate()
        
        assert any("break_duration_max must be greater than or equal to break_duration_min" in e for e in errors)
    
    def test_invalid_quiet_hours_start(self):
        """Test validation error for invalid quiet hours start"""
        config = Configuration(quiet_hours=[(25, 6)])
        errors = config.validate()
        
        assert any("quiet_hours start hour 25 must be between 0 and 23" in e for e in errors)
    
    def test_invalid_quiet_hours_end(self):
        """Test validation error for invalid quiet hours end"""
        config = Configuration(quiet_hours=[(1, 24)])
        errors = config.validate()
        
        assert any("quiet_hours end hour 24 must be between 0 and 23" in e for e in errors)
    
    def test_negative_request_timeout(self):
        """Test validation error for non-positive request_timeout"""
        config = Configuration(request_timeout=0)
        errors = config.validate()
        
        assert "request_timeout must be positive" in errors
    
    def test_negative_max_retries(self):
        """Test validation error for negative max_retries"""
        config = Configuration(max_retries=-1)
        errors = config.validate()
        
        assert "max_retries must be non-negative" in errors
    
    def test_negative_max_redirects(self):
        """Test validation error for negative max_redirects"""
        config = Configuration(max_redirects=-5)
        errors = config.validate()
        
        assert "max_redirects must be non-negative" in errors
    
    def test_invalid_browser_engine(self):
        """Test validation error for invalid browser_engine"""
        config = Configuration(browser_engine="selenium")
        errors = config.validate()
        
        assert "browser_engine must be 'playwright' or 'puppeteer'" in errors
    
    def test_invalid_proxy_rotation_strategy(self):
        """Test validation error for invalid proxy_rotation_strategy"""
        config = Configuration(proxy_rotation_strategy="invalid_strategy")
        errors = config.validate()
        
        assert any("Invalid proxy_rotation_strategy" in e for e in errors)
    
    def test_valid_proxy_rotation_strategies(self):
        """Test that all valid proxy rotation strategies pass validation"""
        valid_strategies = ["per_request", "per_session", "per_n_requests", 
                           "round_robin", "random", "least_used"]
        
        for strategy in valid_strategies:
            config = Configuration(proxy_rotation_strategy=strategy)
            errors = config.validate()
            
            assert not any("proxy_rotation_strategy" in e for e in errors)
    
    def test_negative_proxy_rotation_interval(self):
        """Test validation error for non-positive proxy_rotation_interval"""
        config = Configuration(proxy_rotation_interval=0)
        errors = config.validate()
        
        assert "proxy_rotation_interval must be positive" in errors
    
    def test_invalid_captcha_solver(self):
        """Test validation error for invalid captcha_solver"""
        config = Configuration(captcha_solver="invalid_solver")
        errors = config.validate()
        
        assert any("Invalid captcha_solver" in e for e in errors)
    
    def test_captcha_api_key_required_for_2captcha(self):
        """Test validation error when captcha_api_key missing for 2captcha"""
        config = Configuration(captcha_solver="2captcha", captcha_api_key=None)
        errors = config.validate()
        
        assert any("captcha_api_key is required when using 2captcha" in e for e in errors)
    
    def test_captcha_api_key_required_for_anticaptcha(self):
        """Test validation error when captcha_api_key missing for anticaptcha"""
        config = Configuration(captcha_solver="anticaptcha", captcha_api_key=None)
        errors = config.validate()
        
        assert any("captcha_api_key is required when using anticaptcha" in e for e in errors)
    
    def test_captcha_api_key_not_required_for_manual(self):
        """Test that captcha_api_key is not required for manual solver"""
        config = Configuration(captcha_solver="manual", captcha_api_key=None)
        errors = config.validate()
        
        assert not any("captcha_api_key" in e for e in errors)
    
    def test_invalid_output_format(self):
        """Test validation error for invalid output_format"""
        config = Configuration(output_format="xml")
        errors = config.validate()
        
        assert any("Invalid output_format" in e for e in errors)
    
    def test_empty_output_path(self):
        """Test validation error for empty output_path"""
        config = Configuration(output_path="")
        errors = config.validate()
        
        assert "output_path cannot be empty" in errors
    
    def test_negative_save_interval(self):
        """Test validation error for non-positive save_interval"""
        config = Configuration(save_interval=0)
        errors = config.validate()
        
        assert "save_interval must be positive" in errors
    
    def test_invalid_log_level(self):
        """Test validation error for invalid log_level"""
        config = Configuration(log_level="TRACE")
        errors = config.validate()
        
        assert any("Invalid log_level" in e for e in errors)
    
    def test_valid_log_levels(self):
        """Test that all valid log levels pass validation"""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        
        for level in valid_levels:
            config = Configuration(log_level=level)
            errors = config.validate()
            
            assert not any("log_level" in e for e in errors)
    
    def test_empty_log_file(self):
        """Test validation error for empty log_file"""
        config = Configuration(log_file="")
        errors = config.validate()
        
        assert "log_file cannot be empty" in errors
    
    def test_distributed_mode_requires_redis_url(self):
        """Test validation error when distributed mode enabled without redis_url"""
        config = Configuration(distributed=True, redis_url=None)
        errors = config.validate()
        
        assert "redis_url is required when distributed mode is enabled" in errors
    
    def test_distributed_mode_with_redis_url(self):
        """Test that distributed mode with redis_url passes validation"""
        config = Configuration(distributed=True, redis_url="redis://localhost:6379")
        errors = config.validate()
        
        assert not any("redis_url" in e for e in errors)
    
    def test_multiple_validation_errors(self):
        """Test that multiple validation errors are all reported"""
        config = Configuration(
            base_url="",
            min_delay=-1.0,
            jitter=2.0,
            hourly_limit=0,
            output_format="xml"
        )
        errors = config.validate()
        
        assert len(errors) >= 5
        assert any("base_url" in e for e in errors)
        assert any("min_delay" in e for e in errors)
        assert any("jitter" in e for e in errors)
        assert any("hourly_limit" in e for e in errors)
        assert any("output_format" in e for e in errors)


class TestProxyConfig:
    """Tests for ProxyConfig class"""
    
    def test_proxy_to_url_without_auth(self):
        """Test proxy URL generation without authentication"""
        proxy = ProxyConfig(
            protocol="http",
            host="proxy.example.com",
            port=8080
        )
        
        assert proxy.to_url() == "http://proxy.example.com:8080"
    
    def test_proxy_to_url_with_auth(self):
        """Test proxy URL generation with authentication"""
        proxy = ProxyConfig(
            protocol="http",
            host="proxy.example.com",
            port=8080,
            username="user",
            password="pass"
        )
        
        assert proxy.to_url() == "http://user:pass@proxy.example.com:8080"
    
    def test_proxy_to_dict(self):
        """Test proxy conversion to dictionary"""
        proxy = ProxyConfig(
            protocol="socks5",
            host="proxy.example.com",
            port=1080,
            username="user",
            password="pass"
        )
        
        result = proxy.to_dict()
        
        assert result["protocol"] == "socks5"
        assert result["host"] == "proxy.example.com"
        assert result["port"] == 1080
        assert result["username"] == "user"
        assert result["password"] == "pass"
    
    def test_proxy_from_dict(self):
        """Test proxy creation from dictionary"""
        data = {
            "protocol": "https",
            "host": "proxy.example.com",
            "port": 443,
            "username": "user",
            "password": "pass"
        }
        
        proxy = ProxyConfig.from_dict(data)
        
        assert proxy.protocol == "https"
        assert proxy.host == "proxy.example.com"
        assert proxy.port == 443
        assert proxy.username == "user"
        assert proxy.password == "pass"
    
    def test_proxy_from_dict_without_auth(self):
        """Test proxy creation from dictionary without authentication"""
        data = {
            "protocol": "http",
            "host": "proxy.example.com",
            "port": 8080
        }
        
        proxy = ProxyConfig.from_dict(data)
        
        assert proxy.protocol == "http"
        assert proxy.host == "proxy.example.com"
        assert proxy.port == 8080
        assert proxy.username is None
        assert proxy.password is None


class TestConfigurationToDict:
    """Tests for Configuration.to_dict() method"""
    
    def test_to_dict_with_defaults(self):
        """Test conversion to dictionary with default values"""
        config = Configuration()
        result = config.to_dict()
        
        assert result["base_url"] == "https://affiliate-id.tokopedia.com"
        assert result["min_delay"] == 2.0
        assert result["max_delay"] == 5.0
        assert result["output_format"] == "json"
        assert result["proxies"] == []
    
    def test_to_dict_with_custom_values(self):
        """Test conversion to dictionary with custom values"""
        config = Configuration(
            base_url="https://custom.com",
            min_delay=3.0,
            output_format="csv"
        )
        result = config.to_dict()
        
        assert result["base_url"] == "https://custom.com"
        assert result["min_delay"] == 3.0
        assert result["output_format"] == "csv"
    
    def test_to_dict_with_proxies(self):
        """Test conversion to dictionary with proxies"""
        proxy = ProxyConfig(
            protocol="http",
            host="proxy.example.com",
            port=8080
        )
        config = Configuration(proxies=[proxy])
        result = config.to_dict()
        
        assert len(result["proxies"]) == 1
        assert result["proxies"][0]["protocol"] == "http"
        assert result["proxies"][0]["host"] == "proxy.example.com"
        assert result["proxies"][0]["port"] == 8080


class TestConfigurationEdgeCases:
    """Tests for edge cases and boundary conditions"""
    
    def test_jitter_boundary_values(self):
        """Test jitter at boundary values 0 and 1"""
        config_zero = Configuration(jitter=0.0)
        errors_zero = config_zero.validate()
        assert not any("jitter" in e for e in errors_zero)
        
        config_one = Configuration(jitter=1.0)
        errors_one = config_one.validate()
        assert not any("jitter" in e for e in errors_one)
    
    def test_quiet_hours_boundary_values(self):
        """Test quiet hours at boundary values"""
        config = Configuration(quiet_hours=[(0, 23)])
        errors = config.validate()
        
        assert not any("quiet_hours" in e for e in errors)
    
    def test_max_retries_zero(self):
        """Test that max_retries can be zero (no retries)"""
        config = Configuration(max_retries=0)
        errors = config.validate()
        
        assert not any("max_retries" in e for e in errors)
    
    def test_empty_proxies_list(self):
        """Test that empty proxies list is valid"""
        config = Configuration(proxies=[])
        errors = config.validate()
        
        assert errors == []
    
    def test_multiple_quiet_hours_periods(self):
        """Test multiple quiet hours periods"""
        config = Configuration(quiet_hours=[(1, 6), (13, 14), (22, 23)])
        errors = config.validate()
        
        assert not any("quiet_hours" in e for e in errors)
    
    def test_min_delay_equals_max_delay(self):
        """Test that min_delay can equal max_delay"""
        config = Configuration(min_delay=3.0, max_delay=3.0)
        errors = config.validate()
        
        assert not any("delay" in e for e in errors)
    
    def test_break_duration_min_equals_max(self):
        """Test that break_duration_min can equal break_duration_max"""
        config = Configuration(break_duration_min=900, break_duration_max=900)
        errors = config.validate()
        
        assert not any("break_duration" in e for e in errors)
