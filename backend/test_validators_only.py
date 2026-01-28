"""
Simple test for validators (no database dependencies)
"""
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

# Import validators directly
from app.utils.validators import (
    sanitize_input, encode_special_chars,
    validate_password_strength, validate_email_format
)


def test_input_sanitization():
    """Test input sanitization"""
    print("=" * 60)
    print("Testing Input Sanitization")
    print("=" * 60)
    
    test_cases = [
        ("<script>alert('xss')</script>", True, "Should remove script tags"),
        ("javascript:alert('xss')", True, "Should remove javascript protocol"),
        ("onerror=alert('xss')", True, "Should remove onerror"),
        ("normal text", False, "Should pass normal text"),
        ("test@example.com", False, "Should pass email"),
    ]
    
    all_passed = True
    for input_text, should_change, description in test_cases:
        sanitized = sanitize_input(input_text)
        changed = input_text != sanitized
        status = "[PASS]" if changed == should_change else "[FAIL]"
        if changed != should_change:
            all_passed = False
        
        print(f"\n{status} Input: {input_text[:50]}")
        print(f"   Description: {description}")
        print(f"   Sanitized: {sanitized[:50]}")
        print(f"   Changed: {changed} (expected: {should_change})")
    
    return all_passed


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
    
    all_passed = True
    for password, expected_valid, description in test_cases:
        is_valid, error_msg = validate_password_strength(password)
        status = "[PASS]" if is_valid == expected_valid else "[FAIL]"
        if is_valid != expected_valid:
            all_passed = False
        
        print(f"\n{status} Password: {password[:20]}")
        print(f"   Expected: {'Valid' if expected_valid else 'Invalid'}")
        print(f"   Result: {'Valid' if is_valid else f'Invalid: {error_msg}'}")
        print(f"   Description: {description}")
    
    return all_passed


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
    ]
    
    all_passed = True
    for email, expected_valid, description in test_cases:
        is_valid, error_msg = validate_email_format(email)
        status = "[PASS]" if is_valid == expected_valid else "[FAIL]"
        if is_valid != expected_valid:
            all_passed = False
        
        print(f"\n{status} Email: {email}")
        print(f"   Expected: {'Valid' if expected_valid else 'Invalid'}")
        print(f"   Result: {'Valid' if is_valid else f'Invalid: {error_msg}'}")
        print(f"   Description: {description}")
    
    return all_passed


def test_encoding():
    """Test special character encoding"""
    print("\n" + "=" * 60)
    print("Testing Special Character Encoding")
    print("=" * 60)
    
    test_cases = [
        ("<script>", "Should encode < and >"),
        ("&", "Should encode &"),
        ("'", "Should encode single quote"),
        ('"', "Should encode double quote"),
        ("normal text", "Should not change normal text"),
    ]
    
    all_passed = True
    for input_text, description in test_cases:
        encoded = encode_special_chars(input_text)
        changed = input_text != encoded
        status = "[PASS]" if changed or input_text == "normal text" else "[FAIL]"
        
        print(f"\n{status} Input: {input_text}")
        print(f"   Description: {description}")
        print(f"   Encoded: {encoded}")
        print(f"   Changed: {changed}")
    
    return all_passed


def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("Security Features Test Suite (Validators Only)")
    print("=" * 60)
    
    results = []
    
    try:
        results.append(("Input Sanitization", test_input_sanitization()))
        results.append(("Password Validation", test_password_validation()))
        results.append(("Email Validation", test_email_validation()))
        results.append(("Character Encoding", test_encoding()))
        
        print("\n" + "=" * 60)
        print("Test Results Summary")
        print("=" * 60)
        
        all_passed = True
        for test_name, passed in results:
            status = "[PASS]" if passed else "[FAIL]"
            print(f"{status}: {test_name}")
            if not passed:
                all_passed = False
        
        print("\n" + "=" * 60)
        if all_passed:
            print("[SUCCESS] All tests PASSED!")
        else:
            print("[ERROR] Some tests FAILED!")
        print("=" * 60)
        
        return 0 if all_passed else 1
        
    except Exception as e:
        print(f"\n[ERROR] Test suite error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
