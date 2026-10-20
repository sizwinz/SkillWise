# utils/helpers.py
import re
from datetime import timedelta
from typing import List


def update_progress(
    progress_bar,
    eta_placeholder,
    current_progress,
    total_stages,
    start_time,
    estimated_time,
    stage_name,
):
    """Update progress bar with current stage information without decorative emojis."""
    progress = max(0, min(100, (current_progress / max(total_stages, 1)) * 100))
    progress_bar.progress(int(progress))
    eta_placeholder.text(f"Processing: {stage_name} ({int(progress)}%)")


def clean_task_text(raw_line: str) -> str:
    """Strip list markers, checkboxes, markdown bolding, and trailing duration notes."""
    if not raw_line:
        return ""
    text = raw_line.strip()
    # Strip enclosing bold markdown if present
    if text.startswith("**") and text.endswith("**") and len(text) >= 4:
        text = text[2:-2].strip()
    # Remove leading list markers: bullets, numbered items, checkboxes
    text = re.sub(r"^(\d+[\.\)]|[-*+])\s*(\[[ xX]\])?\s*", "", text).strip()
    # Strip any remaining leading or trailing asterisks
    text = text.strip("*").strip()
    # Remove trailing duration in parentheses or brackets, e.g., "(2 weeks)", "(1-2 weeks)", "(Weeks 1-4)"
    text = re.sub(
        r"\s*[\(\[](?:\d+(?:\.\d+)?(?:\s*-\s*\d+(?:\.\d+)?)?\s*(?:week|day|month|hour)s?|Weeks?\s*\d+\s*(?:-\s*\d+)?)[\)\]]\s*$",
        "",
        text,
        flags=re.IGNORECASE,
    ).strip()
    return text


def generate_task_key(section_name: str, raw_line: str) -> str:
    """Generates a clean, unique identifier for tasks independent of markdown formatting."""
    cleaned_line = clean_task_text(raw_line)
    clean_section = re.sub(r"[*#]", "", section_name or "General").strip()
    return f"{clean_section}::{cleaned_line}"


def is_task_line(line_stripped: str) -> bool:
    """Check if a line represents an actionable learning task or list item."""
    if not line_stripped:
        return False
    s = line_stripped.strip()
    if s.startswith("**") and s.endswith("**") and len(s) > 4:
        s = s[2:-2].strip()
    # Markdown list items: *, -, +
    if s.startswith(("*", "-", "+")):
        if re.match(r"^[-*+]{3,}$", s):
            return False
        # Require space after *, -, + so inline italics "*note*" are not misclassified
        if len(s) > 1 and s[1] in (" ", "\t"):
            return True
        return False
    # Numbered lists: "1. ", "2) "
    if re.match(r"^\d+[\.\)]\s+", s):
        return True
    return False


def is_module_header(line_stripped: str) -> bool:
    """Check if a line is a ### module header or standalone **Bold Header** (and not a bolded task)."""
    if not line_stripped:
        return False
    if line_stripped.startswith("###"):
        return True
    if line_stripped.startswith("**") and line_stripped.endswith("**") and len(line_stripped) > 4:
        inner = line_stripped[2:-2].strip()
        return not is_task_line(inner)
    return False


def parse_duration(duration_str: str) -> timedelta:
    """Parses duration text into a concrete timedelta."""
    if not duration_str:
        return timedelta(weeks=1)

    # Weeks range with or without parentheses: "(Weeks 1-4)" or "Weeks 1 - 4"
    range_match = re.search(r"Weeks?\s*(\d+)\s*-\s*(\d+)", duration_str, re.IGNORECASE)
    if range_match:
        start_w = int(range_match.group(1))
        end_w = int(range_match.group(2))
        return timedelta(weeks=max(1, end_w - start_w + 1))

    # Numeric range with unit: "(1-2 weeks)", "(3-5 days)"
    num_range_match = re.search(
        r"[\(\[]?(\d+)\s*-\s*(\d+)\s*(week|day|month|hour)s?[\)\]]?",
        duration_str,
        re.IGNORECASE,
    )
    if num_range_match:
        high_val = int(num_range_match.group(2))
        unit = num_range_match.group(3).lower()
        if unit == "week":
            return timedelta(weeks=max(1, high_val))
        elif unit == "day":
            return timedelta(days=max(1, high_val))
        elif unit == "month":
            return timedelta(weeks=max(1, high_val * 4))
        elif unit == "hour":
            return timedelta(days=max(1, round(high_val / 4)))

    # Single unit: "(2 weeks)", "(5 days)", "(1 month)"
    unit_match = re.search(
        r"[\(\[]?(\d+(?:\.\d+)?)\s*(week|day|month|hour)s?[\)\]]?",
        duration_str,
        re.IGNORECASE,
    )
    if unit_match:
        val = float(unit_match.group(1))
        unit = unit_match.group(2).lower()
        if unit == "week":
            return timedelta(days=max(1, round(val * 7)))
        elif unit == "day":
            return timedelta(days=max(1, round(val)))
        elif unit == "month":
            return timedelta(weeks=max(1, round(val * 4)))
        elif unit == "hour":
            return timedelta(days=max(1, round(val / 4)))

    return timedelta(weeks=1)


def extract_roadmap_tasks(roadmap_text: str) -> List[str]:
    """
    Extract unique task keys across all supported markdown formatting structures.
    Supports phases (##), modules (### or **), and tasks (*, -, +, 1.).
    """
    if not roadmap_text:
        return []

    tasks = []
    current_section = "General"

    for line in roadmap_text.splitlines():
        line_stripped = line.strip()
        if not line_stripped:
            continue

        # Phase header: "## Phase 1"
        if line_stripped.startswith("##") and not line_stripped.startswith("###"):
            current_section = line_stripped.lstrip("#").strip()
            continue

        # Module header: "### Module 1" or "**Module 1**"
        if is_module_header(line_stripped):
            current_section = line_stripped.lstrip("#*").rstrip("*").strip()
            continue

        # Actionable task item
        if is_task_line(line_stripped):
            cleaned = clean_task_text(line_stripped)
            if cleaned and not cleaned.lower().startswith(("phase", "module", "table of contents")):
                key = generate_task_key(current_section, line_stripped)
                if key not in tasks:
                    tasks.append(key)

    return tasks
