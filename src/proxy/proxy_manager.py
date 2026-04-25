#!/usr/bin/env python3
"""
Universal Proxy Manager
Supports multiple proxy providers: Webshare, Smartproxy, ProxyScrape, etc.
"""

import random
import logging
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
import requests
import time

logger = logging.getLogger(__name__)


@dataclass
class ProxyConfig:
    """Proxy configuration."""
    host: str
    port: int
    username: Optional[str] = None
    password: Optional[str] = None
    protocol: str = "http"  # http, https, socks5
    country: Optional[str] = None
    provider: Optional[str] = None
    
    def to_playwright_format(self) -> Dict[str, Any]:
        """Convert to Playwright proxy format."""
        proxy_dict = {
            "server": f"{self.protocol}://{self.host}:{self.port}"
        }
        
        if self.username and self.password:
            proxy_dict["username"] = self.username
            proxy_dict["password"] = self.password
        
        return proxy_dict
    
    def to_url_format(self) -> str:
        """Convert to URL format for requests."""
        if self.username and self.password:
            return f"{self.protocol}://{self.username}:{self.password}@{self.host}:{self.port}"
        else:
            return f"{self.protocol}://{self.host}:{self.port}"
    
    def __str__(self) -> str:
        return f"{self.host}:{self.port} ({self.provider or 'unknown'})"


class ProxyManager:
    """Manages proxy rotation and validation."""
    
    def __init__(self):
        self.proxies: List[ProxyConfig] = []
        self.working_proxies: List[ProxyConfig] = []
        self.failed_proxies: List[ProxyConfig] = []
        self.current_index = 0
        
    def load_webshare_proxies(self, file_path: str) -> int:
        """Load proxies from Webshare format file.
        
        Format: IP:PORT:USERNAME:PASSWORD
        """
        try:
            with open(file_path, 'r') as f:
                lines = f.readlines()
            
            loaded = 0
            for line in lines:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                parts = line.split(':')
                if len(parts) >= 2:
                    host = parts[0]
                    port = int(parts[1])
                    username = parts[2] if len(parts) > 2 else None
                    password = parts[3] if len(parts) > 3 else None
                    
                    proxy = ProxyConfig(
                        host=host,
                        port=port,
                        username=username,
                        password=password,
                        protocol="http",
                        country="ID",
                        provider="webshare"
                    )
                    
                    self.proxies.append(proxy)
                    loaded += 1
            
            logger.info(f"Loaded {loaded} Webshare proxies from {file_path}")
            return loaded
            
        except Exception as e:
            logger.error(f"Failed to load Webshare proxies: {e}")
            return 0
    
    def load_smartproxy_config(self, host: str, port: int, username: str, password: str) -> int:
        """Load Smartproxy configuration."""
        try:
            proxy = ProxyConfig(
                host=host,
                port=port,
                username=username,
                password=password,
                protocol="http",
                country="ID",
                provider="smartproxy"
            )
            
            self.proxies.append(proxy)
            logger.info(f"Loaded Smartproxy: {host}:{port}")
            return 1
            
        except Exception as e:
            logger.error(f"Failed to load Smartproxy config: {e}")
            return 0
    
    def load_free_proxies(self, file_path: str) -> int:
        """Load free proxies from ProxyScrape format.
        
        Format: IP:PORT (no auth)
        """
        try:
            with open(file_path, 'r') as f:
                lines = f.readlines()
            
            loaded = 0
            for line in lines:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                parts = line.split(':')
                if len(parts) >= 2:
                    host = parts[0]
                    port = int(parts[1])
                    
                    proxy = ProxyConfig(
                        host=host,
                        port=port,
                        protocol="http",
                        country="ID",
                        provider="free"
                    )
                    
                    self.proxies.append(proxy)
                    loaded += 1
            
            logger.info(f"Loaded {loaded} free proxies from {file_path}")
            return loaded
            
        except Exception as e:
            logger.error(f"Failed to load free proxies: {e}")
            return 0
    
    def test_proxy(self, proxy: ProxyConfig, timeout: int = 10) -> bool:
        """Test if proxy is working."""
        try:
            proxies = {
                'http': proxy.to_url_format(),
                'https': proxy.to_url_format()
            }
            
            # Test with a simple request
            response = requests.get(
                'http://httpbin.org/ip',
                proxies=proxies,
                timeout=timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                logger.debug(f"Proxy {proxy} working, IP: {data.get('origin', 'unknown')}")
                return True
            else:
                logger.debug(f"Proxy {proxy} returned status {response.status_code}")
                return False
                
        except Exception as e:
            logger.debug(f"Proxy {proxy} failed: {e}")
            return False
    
    def validate_all_proxies(self, max_workers: int = 5) -> int:
        """Test all proxies and separate working from failed ones."""
        logger.info(f"Testing {len(self.proxies)} proxies...")
        
        self.working_proxies = []
        self.failed_proxies = []
        
        for i, proxy in enumerate(self.proxies):
            logger.info(f"Testing proxy {i+1}/{len(self.proxies)}: {proxy}")
            
            if self.test_proxy(proxy):
                self.working_proxies.append(proxy)
                logger.info(f"✅ Proxy {proxy} is working")
            else:
                self.failed_proxies.append(proxy)
                logger.warning(f"❌ Proxy {proxy} failed")
            
            # Small delay between tests
            time.sleep(1)
        
        logger.info(f"Proxy validation complete: {len(self.working_proxies)} working, {len(self.failed_proxies)} failed")
        return len(self.working_proxies)
    
    def get_random_proxy(self) -> Optional[ProxyConfig]:
        """Get a random working proxy."""
        if not self.working_proxies:
            logger.warning("No working proxies available")
            return None
        
        return random.choice(self.working_proxies)
    
    def get_next_proxy(self) -> Optional[ProxyConfig]:
        """Get next proxy in rotation."""
        if not self.working_proxies:
            logger.warning("No working proxies available")
            return None
        
        proxy = self.working_proxies[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.working_proxies)
        return proxy
    
    def mark_proxy_failed(self, proxy: ProxyConfig):
        """Mark a proxy as failed and remove from working list."""
        if proxy in self.working_proxies:
            self.working_proxies.remove(proxy)
            self.failed_proxies.append(proxy)
            logger.warning(f"Marked proxy {proxy} as failed")
    
    def get_stats(self) -> Dict[str, int]:
        """Get proxy statistics."""
        return {
            'total': len(self.proxies),
            'working': len(self.working_proxies),
            'failed': len(self.failed_proxies)
        }


# Example usage and testing
async def test_proxy_manager():
    """Test the proxy manager."""
    manager = ProxyManager()
    
    # Load different proxy sources
    print("Loading proxies...")
    
    # Try to load from different sources
    webshare_count = manager.load_webshare_proxies("config/webshare_proxies.txt")
    free_count = manager.load_free_proxies("config/free_proxies.txt")
    
    print(f"Loaded {webshare_count} Webshare proxies")
    print(f"Loaded {free_count} free proxies")
    
    if manager.proxies:
        print(f"\nTesting {len(manager.proxies)} proxies...")
        working_count = manager.validate_all_proxies()
        
        stats = manager.get_stats()
        print(f"\nProxy Stats:")
        print(f"  Total: {stats['total']}")
        print(f"  Working: {stats['working']}")
        print(f"  Failed: {stats['failed']}")
        
        if working_count > 0:
            print(f"\n✅ Ready to use {working_count} working proxies!")
            
            # Test getting proxies
            proxy1 = manager.get_random_proxy()
            proxy2 = manager.get_next_proxy()
            
            print(f"Random proxy: {proxy1}")
            print(f"Next proxy: {proxy2}")
        else:
            print("\n❌ No working proxies found!")
    else:
        print("\n⚠️ No proxy files found. Please setup proxy files first.")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_proxy_manager())