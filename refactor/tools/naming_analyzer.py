#!/usr/bin/env python3
"""
Naming Analyzer: Naming Conventions
Detects inconsistent or poor naming patterns
"""

import re
import sys
from pathlib import Path
from typing import Dict, List


class NamingAnalyzer:
    """Analyze and suggest naming improvements"""

    def __init__(self, source: str, filetype: str = "js"):
        self.source = source
        self.source_lines = source.split("\n")
        self.filetype = filetype
        self.issues = []

    def find_unclear_names(self) -> List[Dict]:
        """Find ambiguous or unclear variable names"""
        issues = []
        # Single letter vars (except loop counters)
        bad_patterns = {
            r'\b[a-z]\s*=': 'single_letter_var',
            r'\bx\b|\by\b|\bz\b': 'unclear_var',
            r'\btemp\b|\btmp\b': 'temp_var',
            r'\bnum\b|\bvar\b': 'vague_name',
        }

        for i, line in enumerate(self.source_lines, 1):
            for pattern, issue_type in bad_patterns.items():
                if re.search(pattern, line):
                    issues.append({
                        "issue": issue_type,
                        "line": i,
                        "code": line.strip(),
                        "suggestion": "Use descriptive names instead"
                    })

        return issues

    def find_inconsistent_casing(self) -> List[Dict]:
        """Find inconsistent naming conventions"""
        issues = []

        # Look for snake_case in camelCase context (Vue/JS)
        if self.filetype in ["js", "vue"]:
            snake_case_pattern = r'[a-z]+_[a-z]+'
            camel_case_count = len(re.findall(r'[a-z]+[A-Z]', self.source))

            for i, line in enumerate(self.source_lines, 1):
                if re.search(snake_case_pattern, line) and camel_case_count > 10:
                    match = re.search(snake_case_pattern, line)
                    if match:
                        issues.append({
                            "issue": "snake_case_in_camelcase",
                            "line": i,
                            "code": line.strip(),
                            "found": match.group(),
                            "suggestion": f"Use camelCase: {match.group().replace('_', '')}"
                        })

        return issues

    def find_abbreviations(self) -> List[Dict]:
        """Find excessive abbreviations"""
        issues = []
        abbrev_patterns = [
            (r'\bfn\b', 'fn -> function'),
            (r'\binfo\b.*=', 'info -> information'),
            (r'\bdesc\b', 'desc -> description'),
            (r'\bmgr\b', 'mgr -> manager'),
            (r'\bhelper\b', 'helper -> utilities/services'),
        ]

        for i, line in enumerate(self.source_lines, 1):
            for pattern, suggestion in abbrev_patterns:
                if re.search(pattern, line):
                    issues.append({
                        "issue": "abbreviation",
                        "line": i,
                        "code": line.strip(),
                        "suggestion": suggestion
                    })

        return issues

    def analyze(self) -> List[Dict]:
        """Run all naming analyses"""
        return (
            self.find_unclear_names() +
            self.find_inconsistent_casing() +
            self.find_abbreviations()
        )


def analyze_file(filepath: Path) -> Dict:
    """Analyze file for naming issues"""
    try:
        with open(filepath, "r") as f:
            source = f.read()

        filetype = "vue" if filepath.suffix == ".vue" else filepath.suffix.lstrip(".")
        analyzer = NamingAnalyzer(source, filetype)
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
        print("Usage: naming_analyzer.py <path>")
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
