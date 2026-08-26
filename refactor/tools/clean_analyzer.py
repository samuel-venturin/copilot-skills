#!/usr/bin/env python3
"""
Clean Code Analyzer: SOLID Principles & Best Practices
Detects violations of clean code principles
"""

import re
import sys
from pathlib import Path
from typing import Dict, List


class CleanCodeAnalyzer:
    """Analyze and suggest clean code improvements"""

    def __init__(self, source: str):
        self.source = source
        self.source_lines = source.split("\n")
        self.issues = []

    def find_long_functions(self) -> List[Dict]:
        """Detect functions that are too long (>50 lines)"""
        issues = []
        func_pattern = r'^\s*(function|const\s+\w+\s*=\s*\(|async\s+function)'

        in_function = False
        func_start = 0
        func_name = ""
        brace_count = 0

        for i, line in enumerate(self.source_lines, 1):
            if re.search(func_pattern, line):
                in_function = True
                func_start = i
                func_name = re.search(r'\w+', line).group() if re.search(r'\w+', line) else "unknown"

            if in_function:
                brace_count += line.count('{') - line.count('}')

                if brace_count == 0 and i > func_start:
                    func_length = i - func_start
                    if func_length > 50:
                        issues.append({
                            "issue": "long_function",
                            "line": func_start,
                            "name": func_name,
                            "length": func_length,
                            "suggestion": "Consider breaking into smaller functions"
                        })
                    in_function = False

        return issues

    def find_high_complexity(self) -> List[Dict]:
        """Detect high cyclomatic complexity (too many conditionals)"""
        issues = []

        for i, line in enumerate(self.source_lines, 1):
            if_count = len(re.findall(r'\bif\b', line))
            else_count = len(re.findall(r'\belse\b', line))
            ternary_count = len(re.findall(r'\?', line))

            complexity = if_count + else_count + ternary_count

            if complexity > 5:
                issues.append({
                    "issue": "high_complexity",
                    "line": i,
                    "code": line.strip()[:80],
                    "complexity_score": complexity,
                    "suggestion": "Reduce conditional branches, consider extracting logic"
                })

        return issues

    def find_duplicate_code(self) -> List[Dict]:
        """Detect potential code duplication"""
        issues = []
        # Simple heuristic: look for similar patterns
        lines = [l.strip() for l in self.source_lines if l.strip()]

        # Find repeated code blocks (simplified)
        duplicates = {}
        for i, line in enumerate(lines, 1):
            if len(line) > 30:  # Only check substantial lines
                if line in duplicates:
                    duplicates[line].append(i)
                else:
                    duplicates[line] = [i]

        for code, line_nums in duplicates.items():
            if len(line_nums) > 1:
                issues.append({
                    "issue": "duplicate_code",
                    "lines": line_nums,
                    "code": code[:80],
                    "count": len(line_nums),
                    "suggestion": "Extract into a shared function (DRY principle)"
                })

        return issues

    def find_side_effects(self) -> List[Dict]:
        """Detect functions with side effects (impure functions)"""
        issues = []
        side_effect_patterns = [
            (r'console\.(log|error|warn)', 'console_logging'),
            (r'document\.', 'dom_manipulation'),
            (r'localStorage\.', 'storage_mutation'),
            (r'global\.\w+\s*=', 'global_mutation'),
        ]

        for i, line in enumerate(self.source_lines, 1):
            for pattern, effect_type in side_effect_patterns:
                if re.search(pattern, line):
                    issues.append({
                        "issue": "side_effect",
                        "type": effect_type,
                        "line": i,
                        "code": line.strip(),
                        "suggestion": "Move side effects outside pure functions"
                    })

        return issues

    def find_magic_numbers(self) -> List[Dict]:
        """Detect magic numbers without explanation"""
        issues = []
        magic_pattern = r'[^\s\d]\s*([1-9][0-9]{2,}|[1-9][0-9]{1}[0-9]{2,})'

        for i, line in enumerate(self.source_lines, 1):
            # Skip common patterns like line numbers, years
            if re.search(r'(20\d{2}|19\d{2})', line):
                continue

            matches = re.findall(magic_pattern, line)
            if matches:
                issues.append({
                    "issue": "magic_number",
                    "line": i,
                    "code": line.strip(),
                    "suggestion": "Extract to a named constant"
                })

        return issues

    def analyze(self) -> List[Dict]:
        """Run all clean code analyses"""
        return (
            self.find_long_functions() +
            self.find_high_complexity() +
            self.find_duplicate_code() +
            self.find_side_effects() +
            self.find_magic_numbers()
        )


def analyze_file(filepath: Path) -> Dict:
    """Analyze file for clean code issues"""
    try:
        with open(filepath, "r") as f:
            source = f.read()

        analyzer = CleanCodeAnalyzer(source)
        issues = analyzer.analyze()

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
        print("Usage: clean_analyzer.py <path>")
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
