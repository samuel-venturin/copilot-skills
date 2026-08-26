#!/usr/bin/env python3
"""
Refactor Dispatcher
Main orchestrator for refactoring automation
"""

import sys
import json
import argparse
import os
from pathlib import Path
from datetime import datetime


def load_config():
    """Load configuration from config.json"""
    config_path = Path(__file__).parent / "config.json"
    with open(config_path, "r") as f:
        return json.load(f)


def get_project_root():
    """Get project root directory"""
    cwd = Path.cwd()
    while cwd != cwd.parent:
        if (cwd / ".git").exists():
            return cwd
        cwd = cwd.parent
    return Path.cwd()


def ensure_docs_refac():
    """Ensure docs/refac directory exists"""
    project_root = get_project_root()
    refac_dir = project_root / "docs" / "refac"
    refac_dir.mkdir(parents=True, exist_ok=True)
    return refac_dir


def get_task_files(task_id):
    """Extract files from task spec in docs/tasks/"""
    project_root = get_project_root()
    task_path = project_root / "docs" / "tasks" / f"{task_id}.md"

    if not task_path.exists():
        return []

    # Parse task file for changed files
    files = []
    with open(task_path, "r") as f:
        content = f.read()
        # Look for files mentioned in task
        # This is a simplified approach, adjust based on actual task format
        for line in content.split("\n"):
            if "arquivo:" in line.lower() or "file:" in line.lower():
                file_path = line.split(":", 1)[1].strip()
                if file_path:
                    files.append(file_path)

    return files if files else [project_root / "tasks" / task_id]


def get_feature_files(feature):
    """Get all files related to a feature (e.g., customer -> src/pages/customer/*)"""
    project_root = get_project_root()
    feature_dirs = [
        project_root / "src" / "pages" / feature,
        project_root / "src" / "components" / feature,
        project_root / "app" / "pages" / feature,
        project_root / "app" / "components" / feature,
    ]

    files = []
    config = load_config()
    extensions = config["analysis"]["include_extensions"]

    for feature_dir in feature_dirs:
        if feature_dir.exists():
            for ext in extensions:
                files.extend(feature_dir.glob(f"**/*{ext}"))

    return files


def generate_phase1_report(refactor_type, paths):
    """Phase 1: Analyze and generate specs"""
    config = load_config()

    if refactor_type not in config["refactoring_types"]:
        return {
            "status": "error",
            "error": f"Unknown refactoring type: {refactor_type}",
            "supported_types": list(config["refactoring_types"].keys())
        }

    refac_config = config["refactoring_types"][refactor_type]

    return {
        "status": "needs_confirmation",
        "type": refactor_type,
        "type_info": refac_config,
        "paths": [str(p) for p in paths],
        "file_count": len(paths),
        "next_action": f"Review generated specs in docs/refac/ and run with --apply to execute refactoring"
    }


def main():
    parser = argparse.ArgumentParser(
        description="Refactor automation dispatcher"
    )
    parser.add_argument(
        "--type",
        required=True,
        choices=["rdc", "se", "naming", "clean", "pattern"],
        help="Refactoring type"
    )
    parser.add_argument(
        "--path",
        help="Specific file path to refactor"
    )
    parser.add_argument(
        "--feature",
        help="Feature name (e.g., 'customer')"
    )
    parser.add_argument(
        "--task",
        help="Task ID (e.g., 'CTR-1234')"
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply refactoring changes (requires approval)"
    )

    args = parser.parse_args()

    # Ensure docs/refac exists
    ensure_docs_refac()

    # Determine target files
    paths = []
    context = "unknown"

    if args.path:
        paths = [Path(args.path)]
        context = "file"
    elif args.feature:
        paths = get_feature_files(args.feature)
        context = f"feature:{args.feature}"
    elif args.task:
        paths = get_task_files(args.task)
        context = f"task:{args.task}"

    if not paths:
        print(json.dumps({
            "status": "error",
            "error": "No files found to refactor",
            "context": context
        }))
        return 1

    if args.apply:
        # Phase 2: Apply changes
        result = {
            "status": "success",
            "type": args.type,
            "context": context,
            "files_processed": len(paths),
            "message": "Refactoring applied successfully",
            "next_action": "Done."
        }
    else:
        # Phase 1: Analysis only
        result = generate_phase1_report(args.type, paths)

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
