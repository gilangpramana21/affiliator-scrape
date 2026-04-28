"""Unit tests for CookieValidator"""

import json
import time
from unittest.mock import Mock, patch, mock_open
import pytest
import requests

from src.core.cookie_validator import CookieValidator, ValidationResult


@pytest.fixture
def validator():
    """Create a CookieValidator instance"""
    return CookieValidator()


@pytest.fixture
def valid_cookies():
    """Valid cookie data"""
    return [
        {
            "name": "_SID_Tokopedia_",
            "value": "valid_session_id_123",
            "domain": ".tokopedia.com",
            "path": "/",
            "httpOnly": True,
            "secure": True
        },
        {
            "name": "DID",
            "value": "valid_device_id_456",
            "domain": ".tokopedia.com",
            "path": "/",
            "httpOnly": False,
            "secure": True
        }
    ]


@pytest.fixture
def expired_cookies():
    """Cookies with expiration dates"""
    current_time = int(time.time())
    return [
        {
            "name": "_SID_Tokopedia_",
            "value": "session_id",
            "domain": ".tokopedia.com",
            "path": "/",
            "expirationDate": current_time - 3600  # Expired 1 hour ago
        },
        {
            "name": "DID",
            "value": "device_id",
            "domain": ".tokopedia.com",
            "path": "/",
            "expirationDate": current_time + 86400  # Expires in 24 hours
        }
    ]


# ── validate_format() ─────────────────────────────────────────────────────────

class TestValidateFormat:
    """Tests for validate_format method"""
    
    def test_valid_cookie_format(self, validator, valid_cookies, tmp_path):
        """Test validation of valid cookie format"""
        cookie_file = tmp_path / "cookies.json"
        cookie_file.write_text(json.dumps(valid_cookies))
        
        result = validator.validate_format(str(cookie_file))
        
        assert result.is_valid is True
        assert "valid" in result.message.lower()
        assert len(result.errors) == 0
    
    def test_file_not_found(self, validator):
        """Test validation when cookie file doesn't exist"""
        result = validator.validate_format("nonexistent_file.json")
        
        assert result.is_valid is False
        assert "tidak ditemukan" in result.message.lower()
        assert len(result.errors) > 0
    
    def test_invalid_json_format(self, validator, tmp_path):
        """Test validation with invalid JSON"""
        cookie_file = tmp_path / "invalid.json"
        cookie_file.write_text("{ invalid json }")
        
        result = validator.validate_format(str(cookie_file))
        
        assert result.is_valid is False
        assert "json" in result.message.lower()
        assert len(result.errors) > 0
    
    def test_cookies_not_list(self, validator, tmp_path):
        """Test validation when cookies is not a list"""
        cookie_file = tmp_path / "cookies.json"
        cookie_file.write_text(json.dumps({"name": "cookie"}))
        
        result = validator.validate_format(str(cookie_file))
        
        assert result.is_valid is False
        assert "format" in result.message.lower() or "salah" in result.message.lower()
        assert any("array" in err.lower() or "list" in err.lower() for err in result.errors)
    
    def test_empty_cookies_list(self, validator, tmp_path):
        """Test validation with empty cookies list"""
        cookie_file = tmp_path / "cookies.json"
        cookie_file.write_text(json.dumps([]))
        
        result = validator.validate_format(str(cookie_file))
        
        assert result.is_valid is False
        assert "kosong" in result.message.lower()
        assert any("kosong" in err.lower() for err in result.errors)
    
    def test_cookie_missing_required_fields(self, validator, tmp_path):
        """Test validation when cookies are missing required fields"""
        invalid_cookies = [
            {
                "name": "cookie1",
                # Missing 'value' and 'domain'
            }
        ]
        cookie_file = tmp_path / "cookies.json"
        cookie_file.write_text(json.dumps(invalid_cookies))
        
        result = validator.validate_format(str(cookie_file))
        
        assert result.is_valid is False
        assert len(result.errors) > 0
        assert any("value" in err.lower() for err in result.errors)
        assert any("domain" in err.lower() for err in result.errors)
    
    def test_no_tokopedia_domain(self, validator, tmp_path):
        """Test validation when no Tokopedia domain cookies found"""
        non_tokopedia_cookies = [
            {
                "name": "cookie1",
                "value": "value1",
                "domain": ".example.com"
            }
        ]
        cookie_file = tmp_path / "cookies.json"
        cookie_file.write_text(json.dumps(non_tokopedia_cookies))
        
        result = validator.validate_format(str(cookie_file))
        
        assert result.is_valid is False
        assert any("tokopedia" in err.lower() for err in result.errors)
    
    def test_placeholder_values_detected(self, validator, tmp_path):
        """Test validation detects placeholder values"""
        placeholder_cookies = [
            {
                "name": "_SID_Tokopedia_",
                "value": "GANTI_DENGAN_SESSION_ID_ASLI",
                "domain": ".tokopedia.com"
            }
        ]
        cookie_file = tmp_path / "cookies.json"
        cookie_file.write_text(json.dumps(placeholder_cookies))
        
        result = validator.validate_format(str(cookie_file))
        
        assert result.is_valid is False
        assert any("placeholder" in err.lower() for err in result.errors)
    
    def test_cookie_not_dict(self, validator, tmp_path):
        """Test validation when cookie is not a dictionary"""
        invalid_cookies = [
            "not_a_dict",
            {"name": "valid", "value": "valid", "domain": ".tokopedia.com"}
        ]
        cookie_file = tmp_path / "cookies.json"
        cookie_file.write_text(json.dumps(invalid_cookies))
        
        result = validator.validate_format(str(cookie_file))
        
        assert result.is_valid is False
        assert any("object" in err.lower() or "dict" in err.lower() for err in result.errors)


# ── check_expiration() ────────────────────────────────────────────────────────

class TestCheckExpiration:
    """Tests for check_expiration method"""
    
    def test_no_expiration_dates(self, validator, valid_cookies):
        """Test with cookies that have no expiration dates"""
        result = validator.check_expiration(valid_cookies)
        assert result is True
    
    def test_expired_cookies_detected(self, validator, capsys):
        """Test detection of expired cookies"""
        current_time = int(time.time())
        expired_cookies = [
            {
                "name": "expired_cookie",
                "value": "value",
                "domain": ".tokopedia.com",
                "expirationDate": current_time - 3600  # Expired 1 hour ago
            }
        ]
        
        result = validator.check_expiration(expired_cookies)
        captured = capsys.readouterr()
        
        assert result is False
        assert "expired" in captured.out.lower()
    
    def test_expiring_soon_warning(self, validator, capsys):
        """Test warning for cookies expiring soon"""
        current_time = int(time.time())
        expiring_soon_cookies = [
            {
                "name": "expiring_cookie",
                "value": "value",
                "domain": ".tokopedia.com",
                "expirationDate": current_time + 3600  # Expires in 1 hour
            }
        ]
        
        result = validator.check_expiration(expiring_soon_cookies)
        captured = capsys.readouterr()
        
        assert result is True  # Not expired yet
        assert "24 jam" in captured.out.lower()
    
    def test_valid_expiration_dates(self, validator):
        """Test with valid future expiration dates"""
        current_time = int(time.time())
        valid_cookies = [
            {
                "name": "valid_cookie",
                "value": "value",
                "domain": ".tokopedia.com",
                "expirationDate": current_time + 86400 * 7  # Expires in 7 days
            }
        ]
        
        result = validator.check_expiration(valid_cookies)
        assert result is True
    
    def test_string_expiration_date(self, validator):
        """Test with string format expiration date"""
        cookies_with_string_date = [
            {
                "name": "cookie",
                "value": "value",
                "domain": ".tokopedia.com",
                "expires": "2099-12-31T23:59:59Z"  # Far future
            }
        ]
        
        result = validator.check_expiration(cookies_with_string_date)
        assert result is True


# ── test_cookies() ────────────────────────────────────────────────────────────

class TestTestCookies:
    """Tests for test_cookies method"""
    
    @patch('requests.get')
    def test_valid_cookies_success(self, mock_get, validator, valid_cookies):
        """Test successful validation with valid cookies"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.url = "https://affiliate-id.tokopedia.com/connection/creator"
        mock_response.text = "<html><body>creator affiliate content</body></html>"
        mock_get.return_value = mock_response
        
        result = validator.test_cookies(valid_cookies)
        
        assert result.is_valid is True
        assert "valid" in result.message.lower()
        assert len(result.errors) == 0
    
    @patch('requests.get')
    def test_redirect_to_login_detected(self, mock_get, validator, valid_cookies):
        """Test detection of redirect to login page"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.url = "https://accounts.tokopedia.com/login"
        mock_response.text = "<html><body>login page</body></html>"
        mock_get.return_value = mock_response
        
        result = validator.test_cookies(valid_cookies)
        
        assert result.is_valid is False
        assert "login" in result.message.lower()
        assert any("redirect" in err.lower() for err in result.errors)
    
    @patch('requests.get')
    def test_coba_lagi_page_detected(self, mock_get, validator, valid_cookies):
        """Test detection of 'Coba lagi' blocking page"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.url = "https://affiliate-id.tokopedia.com/connection/creator"
        mock_response.text = "<html><body>Coba lagi nanti</body></html>"
        mock_get.return_value = mock_response
        
        result = validator.test_cookies(valid_cookies)
        
        assert result.is_valid is False
        assert "coba lagi" in result.message.lower()
        assert any("coba lagi" in err.lower() for err in result.errors)
    
    @patch('requests.get')
    def test_http_error_status(self, mock_get, validator, valid_cookies):
        """Test handling of HTTP error status codes"""
        mock_response = Mock()
        mock_response.status_code = 403
        mock_response.url = "https://affiliate-id.tokopedia.com/connection/creator"
        mock_response.text = "Forbidden"
        mock_get.return_value = mock_response
        
        result = validator.test_cookies(valid_cookies)
        
        assert result.is_valid is False
        assert "403" in result.message
    
    @patch('requests.get')
    def test_timeout_error(self, mock_get, validator, valid_cookies):
        """Test handling of request timeout"""
        mock_get.side_effect = requests.exceptions.Timeout()
        
        result = validator.test_cookies(valid_cookies)
        
        assert result.is_valid is False
        assert "timeout" in result.message.lower()
    
    @patch('requests.get')
    def test_connection_error(self, mock_get, validator, valid_cookies):
        """Test handling of connection error"""
        mock_get.side_effect = requests.exceptions.ConnectionError("Connection failed")
        
        result = validator.test_cookies(valid_cookies)
        
        assert result.is_valid is False
        assert "connection" in result.message.lower()
    
    @patch('requests.get')
    def test_unexpected_content(self, mock_get, validator, valid_cookies):
        """Test handling of unexpected page content"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.url = "https://affiliate-id.tokopedia.com/connection/creator"
        mock_response.text = "<html><body>unexpected content</body></html>"
        mock_get.return_value = mock_response
        
        result = validator.test_cookies(valid_cookies)
        
        assert result.is_valid is False
        assert "konten tidak sesuai" in result.message.lower()
    
    @patch('requests.get')
    def test_cookies_converted_to_dict(self, mock_get, validator, valid_cookies):
        """Test that cookies are properly converted to request format"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.url = "https://affiliate-id.tokopedia.com/connection/creator"
        mock_response.text = "<html><body>creator affiliate</body></html>"
        mock_get.return_value = mock_response
        
        validator.test_cookies(valid_cookies)
        
        # Verify cookies were passed correctly
        call_kwargs = mock_get.call_args[1]
        assert 'cookies' in call_kwargs
        assert '_SID_Tokopedia_' in call_kwargs['cookies']
        assert call_kwargs['cookies']['_SID_Tokopedia_'] == 'valid_session_id_123'
    
    @patch('requests.get')
    def test_headers_included(self, mock_get, validator, valid_cookies):
        """Test that proper headers are included in request"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.url = "https://affiliate-id.tokopedia.com/connection/creator"
        mock_response.text = "<html><body>creator affiliate</body></html>"
        mock_get.return_value = mock_response
        
        validator.test_cookies(valid_cookies)
        
        # Verify headers were passed
        call_kwargs = mock_get.call_args[1]
        assert 'headers' in call_kwargs
        assert 'User-Agent' in call_kwargs['headers']
        assert 'Accept-Language' in call_kwargs['headers']


# ── ValidationResult ──────────────────────────────────────────────────────────

class TestValidationResult:
    """Tests for ValidationResult dataclass"""
    
    def test_validation_result_creation(self):
        """Test creating ValidationResult instance"""
        result = ValidationResult(
            is_valid=True,
            message="Success",
            errors=[]
        )
        
        assert result.is_valid is True
        assert result.message == "Success"
        assert result.errors == []
    
    def test_validation_result_with_errors(self):
        """Test ValidationResult with errors"""
        errors = ["Error 1", "Error 2"]
        result = ValidationResult(
            is_valid=False,
            message="Failed",
            errors=errors
        )
        
        assert result.is_valid is False
        assert result.message == "Failed"
        assert len(result.errors) == 2
