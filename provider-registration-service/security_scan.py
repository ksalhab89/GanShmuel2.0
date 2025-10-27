"""
Comprehensive Security Scan for SQL Injection Vulnerabilities
Analyzes all Python files for potential SQL injection patterns
"""
import os
import re
from pathlib import Path

# Dangerous patterns to detect
DANGEROUS_PATTERNS = [
    (r'text\(f["\']', "F-string in SQL query - SQL INJECTION RISK"),
    (r'text\(["\'].*\{.*\}', "String formatting in SQL query - SQL INJECTION RISK"),
    (r'execute\(["\'].*%.*["\']', "%-formatting in SQL query - SQL INJECTION RISK"),
    (r'\.format\(.*\).*execute', "format() in SQL query - SQL INJECTION RISK"),
    (r'\+ .*["\']SELECT', "String concatenation in SQL - SQL INJECTION RISK"),
    (r'["\']WHERE ["\'] \+', "String concatenation for WHERE clause - SQL INJECTION RISK"),
]

# Safe patterns to validate
SAFE_PATTERNS = [
    (r'text\(["\'][^{%]+["\']', "Static SQL with text() - SAFE"),
    (r'WHERE \(:[\w]+ IS NULL OR', "NULL-safe parameterized query - SAFE"),
    (r'VALUES \(:[\w]+', "Parameterized INSERT - SAFE"),
    (r'= :[\w]+', "Parameter binding - SAFE"),
]

def scan_file(file_path):
    """Scan a single Python file for SQL injection vulnerabilities"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
        lines = content.split('\n')

    issues = []
    safe_patterns_found = []

    for line_no, line in enumerate(lines, 1):
        # Check for dangerous patterns
        for pattern, description in DANGEROUS_PATTERNS:
            if re.search(pattern, line, re.IGNORECASE):
                issues.append({
                    'line': line_no,
                    'pattern': pattern,
                    'description': description,
                    'code': line.strip(),
                    'severity': 'HIGH'
                })

        # Check for safe patterns
        for pattern, description in SAFE_PATTERNS:
            if re.search(pattern, line, re.IGNORECASE):
                safe_patterns_found.append({
                    'line': line_no,
                    'pattern': pattern,
                    'description': description,
                    'code': line.strip()[:80]
                })

    return issues, safe_patterns_found

def scan_directory(directory):
    """Scan all Python files in directory"""
    all_issues = {}
    all_safe_patterns = {}

    for root, dirs, files in os.walk(directory):
        # Skip __pycache__ and .venv directories
        dirs[:] = [d for d in dirs if d not in ['__pycache__', '.venv', 'htmlcov', '.pytest_cache']]

        for file in files:
            if file.endswith('.py') and not file.endswith('.backup'):
                file_path = os.path.join(root, file)
                issues, safe_patterns = scan_file(file_path)

                if issues:
                    all_issues[file_path] = issues

                if safe_patterns:
                    all_safe_patterns[file_path] = safe_patterns

    return all_issues, all_safe_patterns

def generate_report(issues, safe_patterns):
    """Generate comprehensive security report"""
    report = []
    report.append("=" * 80)
    report.append("SQL INJECTION VULNERABILITY SCAN REPORT")
    report.append("=" * 80)
    report.append("")

    # Summary
    total_files_scanned = len(set(list(issues.keys()) + list(safe_patterns.keys())))
    total_issues = sum(len(v) for v in issues.values())
    total_safe_patterns = sum(len(v) for v in safe_patterns.values())

    report.append("SUMMARY")
    report.append("-" * 80)
    report.append(f"Files Scanned: {total_files_scanned}")
    report.append(f"SQL Injection Issues Found: {total_issues}")
    report.append(f"Safe SQL Patterns Found: {total_safe_patterns}")
    report.append("")

    # Issues
    if issues:
        report.append("SECURITY ISSUES DETECTED")
        report.append("=" * 80)

        for file_path, file_issues in issues.items():
            report.append(f"\nFile: {file_path}")
            report.append("-" * 80)

            for issue in file_issues:
                report.append(f"  Line {issue['line']}: {issue['description']}")
                report.append(f"  Severity: {issue['severity']}")
                report.append(f"  Code: {issue['code']}")
                report.append(f"  Pattern: {issue['pattern']}")
                report.append("")
    else:
        report.append("NO SECURITY ISSUES DETECTED")
        report.append("=" * 80)
        report.append("")
        report.append("[OK] All SQL queries use safe parameterized patterns")
        report.append("[OK] No string interpolation or concatenation detected")
        report.append("[OK] No f-strings in SQL queries")
        report.append("")

    # Safe patterns
    if safe_patterns:
        report.append("\nSAFE SQL PATTERNS DETECTED")
        report.append("=" * 80)

        for file_path, patterns in safe_patterns.items():
            file_name = os.path.basename(file_path)
            report.append(f"\nFile: {file_name}")
            report.append("-" * 80)

            # Count pattern types
            pattern_counts = {}
            for p in patterns:
                desc = p['description']
                pattern_counts[desc] = pattern_counts.get(desc, 0) + 1

            for desc, count in pattern_counts.items():
                report.append(f"  [OK] {desc}: {count} instances")
            report.append("")

    report.append("=" * 80)
    report.append("SCAN COMPLETE")
    report.append("=" * 80)

    return "\n".join(report)

if __name__ == "__main__":
    # Scan src directory
    print("Starting SQL injection vulnerability scan...")
    print("Scanning directory: src/")
    print("")

    issues, safe_patterns = scan_directory("src")
    report = generate_report(issues, safe_patterns)

    # Print to console
    print(report)

    # Save to file
    with open("SECURITY_SCAN_REPORT.txt", "w", encoding='utf-8') as f:
        f.write(report)

    print("\nReport saved to: SECURITY_SCAN_REPORT.txt")

    # Exit code
    if issues:
        print("\n[ERROR] SQL injection vulnerabilities detected!")
        exit(1)
    else:
        print("\n[OK] No SQL injection vulnerabilities found!")
        exit(0)
