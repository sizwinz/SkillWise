import re
import time

def update_progress(progress_bar, eta_placeholder, current_progress, total_stages, start_time, estimated_time, stage_name):
    """Update progress bar with current stage information."""
    progress = (current_progress / total_stages) * 100
    elapsed = time.time() - start_time
    eta = max(0, estimated_time - elapsed)
    progress_bar.progress(int(progress))
    eta_placeholder.text(f"⏳ {stage_name}... {int(progress)}%")

def generate_task_key(section_name, raw_line):
    """Generates a clean, unique key for tasks independent of markdown decoration."""
    cleaned_line = re.sub(r"^\s*[-*]\s*(\[ \])?", "", raw_line).strip()
    cleaned_line = re.sub(r"\s*\(.*\)\s*$", "", cleaned_line).strip()
    clean_section = re.sub(r"[*#]", "", section_name).strip()
    return f"{clean_section}::{cleaned_line}"

def extract_roadmap_tasks(roadmap_text):
    tasks = []
    current_section = "General"
    for line in roadmap_text.splitlines():
        line_stripped = line.strip()
        if not line_stripped:
            continue
        if line_stripped.startswith("##"):
            current_section = line_stripped[2:].strip()
        elif line_stripped.startswith("**") and line_stripped.endswith("**"):
            current_section = line_stripped[2:-2].strip()
        elif line_stripped.startswith("*") or line_stripped.startswith("-"):
            cleaned = re.sub(r"^\s*[-*]\s*", "", line_stripped).strip()
            if cleaned and not cleaned.startswith("[ ]") and not cleaned.startswith("[x]"):
                tasks.append(generate_task_key(current_section, line_stripped))
    return tasks
