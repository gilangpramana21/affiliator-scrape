#!/usr/bin/env python3
"""
Normalize cookies from Chrome export to Playwright format
Fixes sameSite values: null -> None (or Lax as default)
"""
import json
from pathlib import Path


def normalize_cookies(input_file: str, output_file: str = None):
    """Normalize cookies for Playwright compatibility"""
    
    if output_file is None:
        output_file = input_file
    
    # Read cookies
    with open(input_file, 'r') as f:
        cookies = json.load(f)
    
    # Normalize each cookie
    normalized = []
    for cookie in cookies:
        # Fix sameSite: null -> "Lax" (safe default)
        if cookie.get('sameSite') is None or cookie.get('sameSite') == 'null':
            cookie['sameSite'] = 'Lax'
        
        # Ensure sameSite is one of: Strict, Lax, None
        if cookie.get('sameSite') not in ['Strict', 'Lax', 'None']:
            cookie['sameSite'] = 'Lax'
        
        # Handle special case: secure cookies with sameSite=None
        if cookie.get('sameSite') == 'no_restriction':
            cookie['sameSite'] = 'None'
            cookie['secure'] = True  # sameSite=None requires secure=true
        
        normalized.append(cookie)
    
    # Save normalized cookies
    with open(output_file, 'w') as f:
        json.dump(normalized, f, indent=2)
    
    print(f"✅ Normalized {len(normalized)} cookies")
    print(f"💾 Saved to: {output_file}")


if __name__ == "__main__":
    normalize_cookies("config/cookies.json")
