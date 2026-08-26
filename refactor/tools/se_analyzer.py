#!/usr/bin/env python3
"""
SE Analyzer: Simplify Expressions
Detects complex expressions and suggests simplifications
"""

import re
import sys
from pathlib import Path
from typing import Dict, List


class ExpressionSimplifier:
    """Analyze and suggest expression simplifications"""

    def __init__(self, source: str):
        self.source = source
        self.source_lines = source.split("\n")
        self.issues = []

    def find_nested_ternaries(self) -> List[Dict]:
        """Find nested ternary operators (? : chains)"""
        issues = []
        pattern = r'.*\?.*:.*\?.*:.*'  # Simplified pattern

        for i, line in enumerate(self.source_lines, 1):
            if re.search(pattern, line):
                issues.append({
                    "issue": "nested_ternary",
                    "line": i,
                    "code": line.strip(),
                    "suggestion": "Consider using if/else or switch for clarity"
                })

        return issues

    def find_complex_conditionals(self) -> List[Dict]:
        """Find overly complex conditional expressions"""
        issues = []
        complex_pattern = r'if\s*\([^)]{100,}\)'  # Very long condition

        for i, line in enumerate(self.source_lines, 1):
            if re.search(complex_pattern, line):
                issues.append({
                    "issue": "complex_conditional",
                    "line": i,
                    "code": line.strip()[:80] + "...",
                    "suggestion": "Extract condition to a named variable or function"
                })

        return issues

    def find_long_chains(self) -> List[Dict]:
        """Find overly long method chains"""
        issues = []
        chain_pattern = r'\.\w+\(.*\)\.\w+\(.*\)\.\w+\(.*\)\.\w+\(.*\)\.'

        for i, line in enumerate(self.source_lines, 1):
            if re.search(chain_pattern, line):
                issues.append({
                    "issue": "long_chain",
                    "line": i,
                    "code": line.strip()[:80] + "...",
                    "suggestion": "Break chain into intermediate variables"
                })

        return issues

    def analyze(self) -> List[Dict]:
        """Run all simplification analyses"""
        return (
            self.find_nested_ternaries() +
            self.find_complex_conditionals() +
            self.find_long_chains()
        )


def analyze_file(filepath: Path) -> Dict:
    """Analyze file for simplification opportunities"""
    try:
        with open(filepath, "r") as f:
            source = f.read()

        simplifier = ExpressionSimplifier(source)
        issues = simplifier.analyze()

        return {
            "status": "analyzed",
            "file": str(filepath),
            "issues": issues,
            "issue_count": len(issues)
        }

    except Exception as e:
        return {
            "status": "error",
            "file": str(filepath),
            "error": str(e)
        }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: se_analyzer.py <path>")
        sys.exit(1)

    import json
    path = Path(sys.argv[1])

    if path.is_dir():
        results = []
        for filepath in path.glob("**/*.{js,vue,ts}"):
            if "node_modules" not in str(filepath):
                results.append(analyze_file(filepath))
        print(json.dumps(results, indent=2))
    else:
        print(json.dumps(analyze_file(path), indent=2))
