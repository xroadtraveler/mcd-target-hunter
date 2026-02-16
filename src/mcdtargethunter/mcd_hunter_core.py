"""
MCD Target Hunter - Backend Core

Purpose:
    Scan CNC/MCD output files for target strings (e.g. 'POST-GENERATED') and
    report contextual parent operations, tool changes, and metadata.

Input(s):
    - Variations of .txt file ('.nc', '.V11', etc)

Output(s):
    - CSV file

Author:
    Travis Rillos

Notes:
    - Designed for Windows
    - GUI frontend implemented with PyQt6

Status:
    Stable (v1.0.0, initial public release)
    
Version:
    1.0.0
"""

import os
import json
import csv
import re
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple

__version__ = "1.0.0"

APP_NAME = "MCD Target Hunter"
CONFIG_DIR_NAME = "MCDTargetFinderConfig"
CONFIG_FILE_NAME = "config.json"


def get_config_dir() -> str:
    local_appdata = os.environ.get("LOCALAPPDATA")
    if not local_appdata:
        home = os.path.expanduser("~")
        local_appdata = os.path.join(home, "AppData", "Local")
    return os.path.join(local_appdata, CONFIG_DIR_NAME)


def get_config_path() -> str:
    return os.path.join(get_config_dir(), CONFIG_FILE_NAME)


@dataclass
class AppConfig:
    target_text: str = "POST-GENERATED"
    parent_text: str = "OPERATION NAME"
    use_parent: bool = True

    op_no_text: str = "OPERATION NO. ="
    tool_change_text: str = "M06"

    case_sensitive: bool = False

    input_file_path: str = ""
    output_dir_path: str = ""

    @staticmethod
    def load() -> "AppConfig":
        cfg_path = get_config_path()
        try:
            if os.path.isfile(cfg_path):
                with open(cfg_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return AppConfig(
                    target_text=data.get("target_text", "POST-GENERATED"),
                    parent_text=data.get("parent_text", "OPERATION NAME"),
                    use_parent=bool(data.get("use_parent", True)),
                    op_no_text=data.get("op_no_text", "OPERATION NO. ="),
                    tool_change_text=data.get("tool_change_text", "M06"),
                    case_sensitive=bool(data.get("case_sensitive", False)),
                    input_file_path=data.get("input_file_path", ""),
                    output_dir_path=data.get("output_dir_path", ""),
                )
        except Exception:
            pass
        return AppConfig()

    def save(self) -> None:
        os.makedirs(get_config_dir(), exist_ok=True)
        with open(get_config_path(), "w", encoding="utf-8") as f:
            json.dump(self.__dict__, f, indent=2)


def read_text_file_lines(path: str) -> List[str]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read().splitlines()
    except UnicodeDecodeError:
        with open(path, "r", encoding="cp1252", errors="replace") as f:
            return f.read().splitlines()


def _contains(haystack: str, needle: str, case_sensitive: bool) -> bool:
    if not needle:
        return False
    return needle in haystack if case_sensitive else needle.lower() in haystack.lower()


def _tool_number_match(line: str, case_sensitive: bool) -> bool:
    """
    Tries to match a 'tool number' in many common NC/post styles.

    Matches examples:
      - N52300 T10
      - N52300 T 10
      - N52300 T=10
      - N52300 T="10"
      - N52300 T#10
      - N52300 TOOL 10
      - N52300 TOOL NO. 10
      - N52300 TOOL CALL 10
    """
    if not line:
        return False

    re_flags = 0 if case_sensitive else re.IGNORECASE

    patterns = [
        r"\bT\s*[=#]?\s*\"?\s*\d+\b", # T10, T 10, T=10, T#10, T="10"
        r"\bTOOL\s*(?:NO\.?)?\s*[=:]?\s*\d+\b", # TOOL 10, TOOL NO 10, TOOL NO. 10
        r"\bTOOL\s*CALL\s*\d+\b", # TOOL CALL 10
    ]

    for pat in patterns:
        if re.search(pat, line, flags=re_flags):
            return True
    return False


def scan_file_for_hits(
    input_path: str,
    target_text: str,
    parent_text: str,
    use_parent: bool,
    op_no_text: str,
    tool_change_text: str,
    case_sensitive: bool = False,
) -> Tuple[List[Dict[str, Any]], int]:

    lines = read_text_file_lines(input_path)

    last_parent: Optional[str] = None
    last_op_no: Optional[str] = None
    last_tool_change: Optional[str] = None
    last_tool_number: Optional[str] = None

    rows: List[Dict[str, Any]] = []

    for idx, line in enumerate(lines):
        stripped = line.strip()

        # Update context trackers (capture FULL line)
        if use_parent and parent_text and _contains(stripped, parent_text, case_sensitive):
            last_parent = stripped

        if op_no_text and _contains(stripped, op_no_text, case_sensitive):
            last_op_no = stripped

        if tool_change_text and _contains(stripped, tool_change_text, case_sensitive):
            last_tool_change = stripped

        # IMPORTANT: tool-number tracker must run BEFORE target-hit check
        if _tool_number_match(stripped, case_sensitive):
            last_tool_number = stripped

        # Target hit (one row per hit)
        if target_text and _contains(stripped, target_text, case_sensitive):
            rows.append({
                "hit_index": len(rows) + 1,
                "line_number": idx + 1,
                "target_text": target_text,
                "target_line": stripped,
                "operation_no_line": last_op_no or "",
                "tool_number_line": last_tool_number or "",
                "tool_change_line": last_tool_change or "",
                "parent_line": last_parent or "",
            })

    return rows, len(rows)


def default_csv_report_path_in_dir(input_path: str, output_dir: str) -> str:
    base = os.path.splitext(os.path.basename(input_path))[0]
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return os.path.join(output_dir, f"{base}_MCDTargetHunter_{ts}.csv")


def write_csv_report(report_path: str, rows: List[Dict[str, Any]], total_hits: int) -> None:
    fieldnames = [
        "total_hits",
        "hit_index",
        "line_number",
        "target_text",
        "target_line",
        "operation_no_line",
        "tool_number_line",
        "tool_change_line",
        "parent_line",
    ]

    with open(report_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow({"total_hits": total_hits, **r})