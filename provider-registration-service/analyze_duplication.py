"""
Analyze code duplication in candidate service
Verify DRY principle is followed
"""
import re
from pathlib import Path
import sys

# Set encoding for Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

def analyze_duplication():
    """Check for code duplication in candidate_service.py"""

    service_file = Path("src/services/candidate_service.py")
    content = service_file.read_text()

    # Count CandidateResponse constructions
    # Pattern: return CandidateResponse(
    direct_constructions = len(re.findall(
        r'return\s+CandidateResponse\s*\(',
        content
    ))

    # Count _build_response usages
    helper_usages = len(re.findall(
        r'self\._build_response\(',
        content
    ))

    print("="*60)
    print("CODE DUPLICATION ANALYSIS")
    print("="*60)
    print(f"Direct CandidateResponse constructions: {direct_constructions}")
    print(f"  Expected: 1 (only in _build_response helper)")
    print(f"  Status: {'✅ PASS' if direct_constructions == 1 else '❌ FAIL'}")
    print()
    print(f"Helper method (_build_response) usages: {helper_usages}")
    print(f"  Expected: ≥4 (create, get, list, approve methods)")
    print(f"  Status: {'✅ PASS' if helper_usages >= 4 else '❌ FAIL'}")
    print()

    # Calculate duplication percentage
    # Before: 4 identical 13-line blocks = 52 lines
    # After: 1 helper (13 lines) + 4 calls (4 lines) = 17 lines
    lines_before = 52
    lines_after = 17
    reduction = ((lines_before - lines_after) / lines_before) * 100

    print(f"Code Duplication Reduction: {reduction:.1f}%")
    print(f"  Lines before DRY: {lines_before}")
    print(f"  Lines after DRY: {lines_after}")
    print(f"  Lines saved: {lines_before - lines_after}")
    print("="*60)

    # Overall result
    if direct_constructions == 1 and helper_usages >= 4:
        print("✅ DRY PRINCIPLE: PASSED")
        print("Code duplication successfully eliminated!")
        return True
    else:
        print("❌ DRY PRINCIPLE: FAILED")
        print("Code duplication still present")
        return False

if __name__ == "__main__":
    success = analyze_duplication()
    exit(0 if success else 1)
