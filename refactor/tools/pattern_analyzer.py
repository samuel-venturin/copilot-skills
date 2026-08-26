#!/usr/bin/env python3
"""
Pattern Analyzer: Project Pattern Conformance
Detects deviations from project patterns and suggests refactoring
"""

import re
import sys
import json
from pathlib import Path
from typing import Dict, List, Tuple


class PatternAnalyzer:
    """Analyze files against project patterns"""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.patterns = self._load_patterns()
        self.e2e_patterns = self._load_e2e_patterns()

    def _load_patterns(self) -> Dict:
        """Load patterns from AGENTS.md and referenced docs"""
        patterns = {
            "vue": {
                "script_style": "composition_api_script_setup",
                "data_attributes": "data-testid",
                "imports": "esm",
                "naming": "camelCase"
            },
            "js": {
                "imports": "esm",
                "naming": "camelCase",
                "async_handling": "async_await"
            },
            "css": {
                "naming": "kebab-case"
            }
        }
        return patterns

    def _load_e2e_patterns(self) -> Dict:
        """Load E2E patterns from e2e/docs/BEST_PRACTICES.md and docs/testid-map.md"""
        e2e_docs = self.project_root / "e2e" / "docs" / "BEST_PRACTICES.md"
        testid_map = self.project_root / "docs" / "testid-map.md"

        e2e_patterns = {
            "selectors": "data-testid",
            "navigation": "ui_only",
            "waits": "conditional_only",
            "isolation": "full",
            "test_naming": "should_{behavior}_when_{condition}",
            "valid_testids": []
        }

        if e2e_docs.exists():
            try:
                with open(e2e_docs, "r") as f:
                    content = f.read()
                    # Extract patterns from markdown
                    if "data-testid" in content:
                        e2e_patterns["selectors"] = "data-testid"
                    if "data-test" in content:
                        e2e_patterns["selectors"] = "data-test"
            except Exception as e:
                pass

        # Load valid testids from map
        if testid_map.exists():
            try:
                with open(testid_map, "r") as f:
                    content = f.read()
                    # Extract all testids from markdown using regex
                    # Pattern: `[data-testid="xxx"]` or `xxx` (just the hash)
                    testids = re.findall(r'\[data-testid="([^"]+)"\]', content)
                    e2e_patterns["valid_testids"] = testids
            except Exception as e:
                pass

        return e2e_patterns

    def analyze_vue_file(self, filepath: Path) -> List[Dict]:
        """Analyze Vue file for pattern violations"""
        issues = []

        try:
            with open(filepath, "r") as f:
                content = f.read()

            # Check 1: data-test vs data-testid in tests
            if "spec.ts" in str(filepath) or "e2e" in str(filepath):
                if 'data-test="' in content and 'data-testid=' not in content:
                    issues.append({
                        "pattern": "selector_naming",
                        "current": "data-test",
                        "expected": "data-testid",
                        "reason": "E2E tests should use data-testid per BEST_PRACTICES.md R06",
                        "occurrences": len(re.findall(r'data-test="[^"]*"', content))
                    })

            # Check 2: Script setup syntax
            if "<script" in content:
                if "<script lang=" in content and "setup" not in content:
                    issues.append({
                        "pattern": "script_style",
                        "current": "options_api",
                        "expected": "composition_api_script_setup",
                        "reason": "Use <script setup> for modern Vue 3 patterns"
                    })

            # Check 3: Import style
            common_js_imports = len(re.findall(r'require\(', content))
            if common_js_imports > 0:
                issues.append({
                    "pattern": "import_style",
                    "current": "commonjs",
                    "expected": "esm",
                    "reason": "Use ES6 imports instead of require()",
                    "occurrences": common_js_imports
                })

            return issues

        except Exception as e:
            return [{
                "pattern": "error",
                "error": str(e),
                "file": str(filepath)
            }]

    def analyze_e2e_file(self, filepath: Path) -> List[Dict]:
        """Analyze E2E test file for pattern violations"""
        issues = []

        try:
            with open(filepath, "r") as f:
                content = f.read()

            # Rule R06: Selectors from data-testid only
            if 'data-test="' in content:
                issues.append({
                    "pattern": "e2e_selector",
                    "current": "data-test",
                    "expected": "data-testid",
                    "rule": "R06",
                    "reason": "Selectors must use data-testid per docs/testid-map.md",
                    "occurrences": len(re.findall(r'data-test="[^"]*"', content))
                })

            # Validate testids exist in map
            valid_testids = self.e2e_patterns.get("valid_testids", [])
            if valid_testids:
                # Extract testids from file
                file_testids = re.findall(r'\[data-testid="([^"]+)"\]', content)
                invalid_testids = [t for t in file_testids if t not in valid_testids]

                if invalid_testids:
                    issues.append({
                        "pattern": "e2e_invalid_testid",
                        "current": "hardcoded_or_invalid",
                        "expected": "from_docs_testid_map",
                        "rule": "R06",
                        "reason": "Testids must be from docs/testid-map.md (generated by /testid-extractor)",
                        "invalid_testids": invalid_testids[:5],  # Show first 5
                        "count": len(invalid_testids),
                        "suggestion": "Run /testid-extractor to regenerate valid testids, or use correct testids from map"
                    })

            # Rule R07: No waitForTimeout
            if "waitForTimeout" in content:
                issues.append({
                    "pattern": "e2e_wait",
                    "current": "waitForTimeout",
                    "expected": "conditional_wait",
                    "rule": "R07",
                    "reason": "Use conditional waits (waitForSelector) instead of timeout"
                })

            # Rule R01: Check for hardcoded navigation bypass
            if "page.goto(" in content and '"/customer/' in content:
                issues.append({
                    "pattern": "e2e_navigation",
                    "current": "direct_goto",
                    "expected": "ui_navigation",
                    "rule": "R01",
                    "reason": "Navigate via UI (clicks) not direct goto() except in smoke/setup"
                })

            # Test naming convention: should {behavior} when {condition}
            test_names = re.findall(r"test\('([^']+)'", content)
            bad_names = [name for name in test_names if not re.match(r"should\s+\w+\s+when\s+", name)]
            if bad_names:
                issues.append({
                    "pattern": "e2e_naming",
                    "current": "non_standard",
                    "expected": "should_{behavior}_when_{condition}",
                    "rule": "R09",
                    "reason": "Test names must follow 'should X when Y' pattern",
                    "examples": bad_names[:3]
                })

            return issues

        except Exception as e:
            return [{
                "pattern": "error",
                "error": str(e),
                "file": str(filepath)
            }]

    def analyze_js_file(self, filepath: Path) -> List[Dict]:
        """Analyze JavaScript file for pattern violations"""
        issues = []

        try:
            with open(filepath, "r") as f:
                content = f.read()

            # Check import style
            common_js_imports = len(re.findall(r'require\(', content))
            if common_js_imports > 0:
                issues.append({
                    "pattern": "import_style",
                    "current": "commonjs",
                    "expected": "esm",
                    "reason": "Use ES6 imports instead of require()"
                })

            # Check naming convention
            snake_case_vars = re.findall(r'(const|let|var)\s+[a-z_]+_[a-z_]+\s*=', content)
            if snake_case_vars:
                issues.append({
                    "pattern": "naming_convention",
                    "current": "snake_case",
                    "expected": "camelCase",
                    "reason": "Use camelCase for variables in JavaScript",
                    "occurrences": len(snake_case_vars)
                })

            return issues

        except Exception as e:
            return [{
                "pattern": "error",
                "error": str(e),
                "file": str(filepath)
            }]

    def analyze(self, filepath: Path) -> Dict:
        """Analyze file against project patterns"""
        if not filepath.exists():
            return {
                "status": "error",
                "error": f"File not found: {filepath}"
            }

        issues = []

        if filepath.suffix == ".vue":
            issues = self.analyze_vue_file(filepath)
        elif "spec.ts" in str(filepath) or "e2e" in str(filepath):
            issues = self.analyze_e2e_file(filepath)
        elif filepath.suffix in [".js", ".jsx", ".ts", ".tsx"]:
            issues = self.analyze_js_file(filepath)

        return {
            "status": "analyzed" if not any(i.get("pattern") == "error" for i in issues) else "error",
            "file": str(filepath),
            "file_type": filepath.suffix,
            "patterns_checked": self._get_patterns_for_file(filepath),
            "issues": issues,
            "issue_count": len([i for i in issues if i.get("pattern") != "error"])
        }

    def _get_patterns_for_file(self, filepath: Path) -> List[str]:
        """Get applicable patterns for file type"""
        if filepath.suffix == ".vue":
            return ["script_style", "data_attributes", "imports", "naming"]
        elif "spec.ts" in str(filepath) or "e2e" in str(filepath):
            return ["selectors", "navigation", "waits", "naming", "isolation"]
        elif filepath.suffix in [".js", ".jsx", ".ts", ".tsx"]:
            return ["imports", "naming"]
        return []


def analyze_file(filepath: Path, project_root: Path = None) -> Dict:
    """Analyze file for pattern violations"""
    if project_root is None:
        project_root = Path.cwd()
        # Try to find git root
        cwd = Path.cwd()
        while cwd != cwd.parent:
            if (cwd / ".git").exists():
                project_root = cwd
                break
            cwd = cwd.parent

    analyzer = PatternAnalyzer(project_root)
    return analyzer.analyze(filepath)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: pattern_analyzer.py <file_path>")
        sys.exit(1)

    filepath = Path(sys.argv[1])
    result = analyze_file(filepath)
    print(json.dumps(result, indent=2))
