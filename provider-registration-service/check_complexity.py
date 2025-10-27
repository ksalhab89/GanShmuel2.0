"""Check cyclomatic complexity of helper method"""
import ast
from pathlib import Path
import sys

# Set encoding for Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

def calculate_complexity(node):
    """Calculate cyclomatic complexity of a function"""
    complexity = 1
    for child in ast.walk(node):
        if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
            complexity += 1
        elif isinstance(child, ast.BoolOp):
            complexity += len(child.values) - 1
    return complexity

def check_complexity():
    """Verify _build_response has low complexity"""

    service_file = Path("src/services/candidate_service.py")
    content = service_file.read_text()

    tree = ast.parse(content)

    print("="*60)
    print("CYCLOMATIC COMPLEXITY ANALYSIS")
    print("="*60)

    found = False
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "_build_response":
            found = True
            complexity = calculate_complexity(node)

            print(f"Method: {node.name}")
            print(f"Complexity: {complexity}")
            print(f"Lines: {node.lineno}-{node.end_lineno}")

            # Map complexity to grade (A=1-5, B=6-10, C=11-20, D=21-30, F=31+)
            if complexity <= 5:
                grade = "A"
                status = "✅ PASS (Low complexity)"
            elif complexity <= 10:
                grade = "B"
                status = "✅ PASS (Acceptable complexity)"
            elif complexity <= 20:
                grade = "C"
                status = "⚠️  WARNING (Consider simplification)"
            else:
                grade = "D"
                status = "❌ FAIL (High complexity)"

            print(f"Grade: {grade}")
            print(f"Status: {status}")
            print("="*60)
            return complexity <= 5

    if not found:
        print("❌ _build_response method not found")
        print("="*60)
        return False

if __name__ == "__main__":
    success = check_complexity()
    exit(0 if success else 1)
