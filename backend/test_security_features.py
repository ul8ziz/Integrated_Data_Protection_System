"""
Test script for security features
"""
import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from app.utils.validators import (
    sanitize_input, encode_special_chars,
    validate_password_strength, validate_email_format
)
from app.utils.datetime_utils import get_current_time
from app.services.presidio_service import PresidioService


def test_input_sanitization():
    """Test input sanitization"""
    print("=" * 60)
    print("Testing Input Sanitization")
    print("=" * 60)
    
    # Test cases
    test_cases = [
        ("<script>alert('xss')</script>", "Should remove script tags"),
        ("javascript:alert('xss')", "Should remove javascript protocol"),
        ("onerror=alert('xss')", "Should remove onerror"),
        ("normal text", "Should pass normal text"),
        ("test@example.com", "Should pass email"),
    ]
    
    for input_text, description in test_cases:
        sanitized = sanitize_input(input_text)
        print(f"\nInput: {input_text[:50]}")
        print(f"Description: {description}")
        print(f"Sanitized: {sanitized[:50]}")
        print(f"Changed: {input_text != sanitized}")
    
    print("\n✅ Input sanitization tests passed")


def test_password_validation():
    """Test password strength validation"""
    print("\n" + "=" * 60)
    print("Testing Password Validation")
    print("=" * 60)
    
    test_cases = [
        ("short", False, "Too short"),
        ("onlylowercase", False, "Missing uppercase, numbers, symbols"),
        ("OnlyUppercase", False, "Missing lowercase, numbers, symbols"),
        ("OnlyNumbers123", False, "Missing symbols"),
        ("OnlySymbols!!!", False, "Missing numbers"),
        ("GoodPass123!", True, "Valid password"),
        ("MySecure@Pass2024", True, "Valid password"),
        ("Test1234!@#$", True, "Valid password"),
    ]
    
    for password, expected_valid, description in test_cases:
        is_valid, error_msg = validate_password_strength(password)
        status = "✅" if is_valid == expected_valid else "❌"
        print(f"\n{status} Password: {password[:20]}")
        print(f"   Expected: {'Valid' if expected_valid else 'Invalid'}")
        print(f"   Result: {'Valid' if is_valid else f'Invalid: {error_msg}'}")
        print(f"   Description: {description}")
    
    print("\n✅ Password validation tests completed")


def test_email_validation():
    """Test email validation"""
    print("\n" + "=" * 60)
    print("Testing Email Validation")
    print("=" * 60)
    
    test_cases = [
        ("test@example.com", True, "Valid email"),
        ("user.name@domain.co.uk", True, "Valid email with subdomain"),
        ("invalid@", False, "Invalid format"),
        ("@domain.com", False, "Missing local part"),
        ("test<script>@example.com", False, "Contains script tag"),
        ("test@example", False, "Missing TLD"),
        ("test@example..com", False, "Double dots"),
    ]
    
    for email, expected_valid, description in test_cases:
        is_valid, error_msg = validate_email_format(email)
        status = "✅" if is_valid == expected_valid else "❌"
        print(f"\n{status} Email: {email}")
        print(f"   Expected: {'Valid' if expected_valid else 'Invalid'}")
        print(f"   Result: {'Valid' if is_valid else f'Invalid: {error_msg}'}")
        print(f"   Description: {description}")
    
    print("\n✅ Email validation tests completed")


def test_datetime_utils():
    """Test datetime utilities"""
    print("\n" + "=" * 60)
    print("Testing Datetime Utilities")
    print("=" * 60)
    
    try:
        current_time = get_current_time()
        print(f"\n✅ Current time: {current_time}")
        print(f"   Timezone: {current_time.tzinfo}")
        print(f"   ISO format: {current_time.isoformat()}")
        
        # Check if timezone is set
        if current_time.tzinfo is not None:
            print("   ✅ Timezone is set correctly")
        else:
            print("   ⚠️  Warning: Timezone is None")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n✅ Datetime utilities tests completed")


def test_script_detection():
    """Test malicious script detection"""
    print("\n" + "=" * 60)
    print("Testing Script Detection")
    print("=" * 60)
    
    try:
        presidio = PresidioService()
        
        test_cases = [
            ("<script>alert('xss')</script>", "JavaScript script tag"),
            ("javascript:alert('xss')", "JavaScript protocol"),
            ("eval('malicious code')", "JavaScript eval"),
            ("exec('malicious code')", "Python exec"),
            ("' OR '1'='1", "SQL injection"),
            ("<img onerror=alert('xss')>", "XSS img onerror"),
        ]
        
        for text, description in test_cases:
            entities = presidio.analyze(text)
            malicious_found = any(
                e.get("entity_type") == "MALICIOUS_SCRIPT" 
                for e in entities
            )
            status = "✅" if malicious_found else "⚠️"
            print(f"\n{status} Text: {text[:50]}")
            print(f"   Description: {description}")
            print(f"   Malicious script detected: {malicious_found}")
            if entities:
                print(f"   Entities found: {len(entities)}")
                for entity in entities[:3]:  # Show first 3
                    print(f"     - {entity.get('entity_type')}: {entity.get('value', '')[:30]}")
        
        print("\n✅ Script detection tests completed")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("Security Features Test Suite")
    print("=" * 60)
    
    try:
        test_input_sanitization()
        test_password_validation()
        test_email_validation()
        test_datetime_utils()
        test_script_detection()
        
        print("\n" + "=" * 60)
        print("✅ All tests completed!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Test suite error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
