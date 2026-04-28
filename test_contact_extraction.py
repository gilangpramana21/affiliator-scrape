#!/usr/bin/env python3
"""
Test script untuk contact extraction
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from core.contact_extractor import ContactExtractor


def test_whatsapp_extraction():
    """Test WhatsApp extraction dengan berbagai format"""
    extractor = ContactExtractor()
    
    print("\n" + "="*80)
    print("🧪 TEST WHATSAPP EXTRACTION")
    print("="*80 + "\n")
    
    test_cases = [
        # Test case 1: wa.me link
        (
            '<a href="https://wa.me/628123456789">Contact me</a>',
            "+628123456789"
        ),
        # Test case 2: Plain text
        (
            '<div>WhatsApp: 0812-3456-7890</div>',
            "+628123456790"
        ),
        # Test case 3: tel: link
        (
            '<a href="tel:+628123456789">Call me</a>',
            "+628123456789"
        ),
        # Test case 4: Text with WA:
        (
            '<span>WA: 08123456789</span>',
            "+628123456789"
        ),
    ]
    
    passed = 0
    failed = 0
    
    for i, (html, expected) in enumerate(test_cases, 1):
        result = extractor.extract_whatsapp(html)
        
        if result == expected:
            print(f"✅ Test {i}: PASS")
            print(f"   Expected: {expected}")
            print(f"   Got: {result}\n")
            passed += 1
        else:
            print(f"❌ Test {i}: FAIL")
            print(f"   Expected: {expected}")
            print(f"   Got: {result}\n")
            failed += 1
    
    print(f"Results: {passed} passed, {failed} failed\n")


def test_email_extraction():
    """Test Email extraction dengan berbagai format"""
    extractor = ContactExtractor()
    
    print("="*80)
    print("🧪 TEST EMAIL EXTRACTION")
    print("="*80 + "\n")
    
    test_cases = [
        # Test case 1: mailto link
        (
            '<a href="mailto:creator@example.com">Email me</a>',
            "creator@example.com"
        ),
        # Test case 2: Plain text
        (
            '<div>Email: affiliator@gmail.com</div>',
            "affiliator@gmail.com"
        ),
        # Test case 3: In paragraph
        (
            '<p>Contact me at: business@tokopedia.com</p>',
            "business@tokopedia.com"
        ),
    ]
    
    passed = 0
    failed = 0
    
    for i, (html, expected) in enumerate(test_cases, 1):
        result = extractor.extract_email(html)
        
        if result == expected:
            print(f"✅ Test {i}: PASS")
            print(f"   Expected: {expected}")
            print(f"   Got: {result}\n")
            passed += 1
        else:
            print(f"❌ Test {i}: FAIL")
            print(f"   Expected: {expected}")
            print(f"   Got: {result}\n")
            failed += 1
    
    print(f"Results: {passed} passed, {failed} failed\n")


def test_combined_extraction():
    """Test extraction keduanya sekaligus"""
    extractor = ContactExtractor()
    
    print("="*80)
    print("🧪 TEST COMBINED EXTRACTION")
    print("="*80 + "\n")
    
    html = """
    <div class="profile">
        <div class="contact-info">
            <p>Hubungi saya:</p>
            <p>WhatsApp: 0812-3456-7890</p>
            <p>Email: creator@example.com</p>
        </div>
    </div>
    """
    
    contacts = extractor.extract_contacts(html)
    
    print("Input HTML:")
    print(html)
    print("\nExtracted:")
    print(f"  WhatsApp: {contacts.get('whatsapp')}")
    print(f"  Email: {contacts.get('email')}")
    
    if contacts.get('whatsapp') and contacts.get('email'):
        print("\n✅ Both contacts extracted successfully!\n")
    else:
        print("\n⚠️  Some contacts missing\n")


if __name__ == "__main__":
    test_whatsapp_extraction()
    test_email_extraction()
    test_combined_extraction()
    
    print("="*80)
    print("✅ TESTING COMPLETED")
    print("="*80)
    print("\nJika semua test PASS, contact extractor siap digunakan!")
    print("Jika ada yang FAIL, perlu adjust regex patterns atau selectors.\n")
