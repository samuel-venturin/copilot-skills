#!/usr/bin/env python3
"""
TestID Parser
Parse testid-v2 hashes and detect patterns
"""

import re
import sys
import json
from typing import Dict, List, Tuple
from dataclasses import dataclass


@dataclass
class TestIDPattern:
    """Represents a testid pattern"""
    hash_base: str  # Base 10-char hash
    pattern_type: str  # "root", "table-col", "table-row", "item", "interactive"
    full_testid: str
    indices: Dict = None  # {"col": 2, "row": 3, "item": 1, "interactive": 0}
    selector: str = None


class TestIDParser:
    """Parse testid-v2 hashes and patterns"""

    # Regex patterns for different testid formats
    PATTERNS = {
        # Root component: a3b9f1c204
        "root": r"^([a-z0-9]{10})$",
        # Table col: a3b9f1c204-col-2
        "table_col": r"^([a-z0-9]{10})-col-(\d+)$",
        # Table row: a3b9f1c204-row-3
        "table_row": r"^([a-z0-9]{10})-row-(\d+)$",
        # Table cell: a3b9f1c204-row-3-col-2
        "table_cell": r"^([a-z0-9]{10})-row-(\d+)-col-(\d+)$",
        # Item in list: a3b9f1c204-item-1
        "list_item": r"^([a-z0-9]{10})-item-(\d+)$",
        # Nested item: a3b9f1c204-item-1-item-2
        "nested_item": r"^([a-z0-9]{10})-item-(\d+)-item-(\d+)$",
        # Interactive (button, input, etc): a3b9f1c204-button-1
        "interactive": r"^([a-z0-9]{10})-(button|input|select|div|span|a)-(\d+)$",
        # Table row interactive: a3b9f1c204-row-1-button-0
        "table_row_interactive": r"^([a-z0-9]{10})-row-(\d+)-(button|input|select|div|span|a)-(\d+)$",
        # Table cell interactive: a3b9f1c204-row-1-col-1-button-1
        "table_cell_interactive": r"^([a-z0-9]{10})-row-(\d+)-col-(\d+)-(button|input|select|div|span|a)-(\d+)$",
        # Item interactive: a3b9f1c204-item-2-input-1
        "item_interactive": r"^([a-z0-9]{10})-item-(\d+)-(button|input|select|div|span|a)-(\d+)$",
    }

    def parse(self, testid: str) -> TestIDPattern:
        """Parse a testid and return pattern info"""

        # Try each pattern in order
        pattern_order = [
            # Most specific first
            "table_cell_interactive",
            "table_row_interactive",
            "item_interactive",
            "table_cell",
            "table_col",
            "table_row",
            "nested_item",
            "list_item",
            "interactive",
            "root"
        ]

        for pattern_name in pattern_order:
            regex = self.PATTERNS[pattern_name]
            match = re.match(regex, testid)

            if match:
                groups = match.groups()
                testid_obj = TestIDPattern(
                    hash_base=groups[0],
                    pattern_type=pattern_name,
                    full_testid=testid,
                    selector=f'[data-testid="{testid}"]'
                )

                # Extract indices based on pattern
                if pattern_name == "table_col":
                    testid_obj.indices = {"col": int(groups[1])}
                elif pattern_name == "table_row":
                    testid_obj.indices = {"row": int(groups[1])}
                elif pattern_name == "table_cell":
                    testid_obj.indices = {"row": int(groups[1]), "col": int(groups[2])}
                elif pattern_name == "list_item":
                    testid_obj.indices = {"item": int(groups[1])}
                elif pattern_name == "nested_item":
                    testid_obj.indices = {"item": int(groups[1]), "nested_item": int(groups[2])}
                elif pattern_name == "interactive":
                    testid_obj.indices = {"tag": groups[1], "index": int(groups[2])}
                elif pattern_name == "table_row_interactive":
                    testid_obj.indices = {"row": int(groups[1]), "tag": groups[2], "index": int(groups[3])}
                elif pattern_name == "table_cell_interactive":
                    testid_obj.indices = {"row": int(groups[1]), "col": int(groups[2]), "tag": groups[3], "index": int(groups[4])}
                elif pattern_name == "item_interactive":
                    testid_obj.indices = {"item": int(groups[1]), "tag": groups[2], "index": int(groups[3])}

                return testid_obj

        # Invalid testid
        return TestIDPattern(
            hash_base="unknown",
            pattern_type="invalid",
            full_testid=testid,
            selector=f'[data-testid="{testid}"]'
        )

    def get_pattern_counts(self, testids: List[str]) -> Dict[str, int]:
        """Count testids by pattern type"""
        counts = {}
        for testid in testids:
            pattern = self.parse(testid)
            pattern_type = pattern.pattern_type
            counts[pattern_type] = counts.get(pattern_type, 0) + 1
        return counts

    def group_by_hash(self, testids: List[str]) -> Dict[str, List[str]]:
        """Group testids by their base hash"""
        groups = {}
        for testid in testids:
            pattern = self.parse(testid)
            hash_base = pattern.hash_base
            if hash_base not in groups:
                groups[hash_base] = []
            groups[hash_base].append(testid)
        return groups


def analyze_testids(testids: List[str]) -> Dict:
    """Analyze a list of testids and return statistics"""
    parser = TestIDParser()

    results = {
        "total_testids": len(testids),
        "unique_hashes": len(set(p.parse(t).hash_base for t in testids if "invalid" not in p.parse(t).pattern_type)),
        "pattern_distribution": parser.get_pattern_counts(testids),
        "hash_groups": parser.group_by_hash(testids),
        "invalid_testids": [t for t in testids if parser.parse(t).pattern_type == "invalid"]
    }

    return results


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: testid_parser.py <testid1> [testid2] ...")
        sys.exit(1)

    testids = sys.argv[1:]
    analysis = analyze_testids(testids)
    print(json.dumps(analysis, indent=2))
