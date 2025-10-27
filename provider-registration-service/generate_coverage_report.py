"""Generate and analyze test coverage"""
import subprocess
import sys
import json
from pathlib import Path


def generate_coverage():
    """Generate test coverage report"""

    print("=" * 60)
    print("GENERATING TEST COVERAGE REPORT")
    print("=" * 60)
    print()

    # Run pytest with coverage
    result = subprocess.run(
        [
            "pytest",
            "tests/",
            "--cov=src",
            "--cov-report=term-missing",
            "--cov-report=html",
            "--cov-report=json",
            "-v",
            "--tb=short"
        ],
        capture_output=True,
        text=True
    )

    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)

    # Parse coverage.json for detailed analysis
    coverage_file = Path("coverage.json")
    if coverage_file.exists():
        with open(coverage_file) as f:
            coverage_data = json.load(f)

        print()
        print("=" * 60)
        print("DETAILED COVERAGE ANALYSIS")
        print("=" * 60)
        print()

        # Overall coverage
        total_coverage = coverage_data["totals"]["percent_covered"]
        print(f"Overall Coverage: {total_coverage:.2f}%")
        print(f"Target: >90%")
        print(f"Status: {'✅ PASS' if total_coverage >= 90 else '❌ FAIL'}")
        print()

        # Per-file coverage
        print("Per-File Coverage:")
        print("-" * 60)

        files = coverage_data.get("files", {})
        file_coverage = []

        for filepath, data in files.items():
            if filepath.startswith("src/"):
                summary = data["summary"]
                percent = summary["percent_covered"]
                file_coverage.append((filepath, percent, summary))

                # Highlight critical files
                is_critical = any(
                    critical in filepath
                    for critical in ["routers/candidates.py", "services/candidate_service.py"]
                )

                status = "✅" if percent == 100 else "⚠️" if percent >= 90 else "❌"
                critical_marker = " [CRITICAL]" if is_critical else ""
                print(f"{status} {filepath}{critical_marker}: {percent:.1f}%")

        print()

        # Identify gaps
        print("=" * 60)
        print("COVERAGE GAPS")
        print("=" * 60)
        print()

        gaps_found = False
        for filepath, percent, summary in file_coverage:
            if percent < 90:
                gaps_found = True
                missing_lines = summary.get("missing_lines", 0)
                print(f"❌ {filepath}: {percent:.1f}% ({missing_lines} lines uncovered)")

        if not gaps_found:
            print("✅ No coverage gaps found!")

        print()
        print("=" * 60)
        print(f"HTML Report: file://{Path('htmlcov/index.html').absolute()}")
        print("=" * 60)
        print()

        return total_coverage >= 90
    else:
        print("ERROR: coverage.json not found")
        # Try to parse from terminal output
        for line in result.stdout.split("\n"):
            if "TOTAL" in line:
                parts = line.split()
                if len(parts) >= 4:
                    coverage_pct = parts[-1].rstrip("%")
                    try:
                        coverage = float(coverage_pct)
                        print()
                        print("=" * 60)
                        print(f"OVERALL COVERAGE: {coverage}%")
                        print(f"TARGET: >90%")
                        print(f"STATUS: {'✅ PASS' if coverage >= 90 else '❌ FAIL'}")
                        print("=" * 60)
                        print()
                        print(f"HTML Report: file://{Path('htmlcov/index.html').absolute()}")
                        print()

                        return coverage >= 90
                    except ValueError:
                        pass

        return False


if __name__ == "__main__":
    success = generate_coverage()
    sys.exit(0 if success else 1)
