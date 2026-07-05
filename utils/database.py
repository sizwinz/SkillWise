import os
import json
import hashlib

def roadmap_id(resume, goal, role):
    base = (resume.strip() + goal.strip() + role.strip()).encode("utf-8")
    return hashlib.sha256(base).hexdigest()[:16]

def load_roadmaps_db(db_path):
    if os.path.exists(db_path):
        with open(db_path, "r") as f:
            try:
                return json.load(f)
            except Exception:
                return []
    return []

def save_roadmaps_db(roadmaps, db_path):
    with open(db_path, "w") as f:
        json.dump(roadmaps, f, indent=2)

def get_active_roadmap(roadmaps_db):
    for r in roadmaps_db:
        if r.get("active"):
            return r
    return None

def sync_progress_from_active_roadmap(roadmaps_db, extract_roadmap_tasks_func):
    active = get_active_roadmap(roadmaps_db)
    if active is not None:
        roadmap_tasks = extract_roadmap_tasks_func(active["roadmap"])
        if "progress" not in active or not isinstance(active["progress"], dict):
            active["progress"] = {task: False for task in roadmap_tasks}
        else:
            # Add missing tasks
            for task in roadmap_tasks:
                if task not in active["progress"]:
                    active["progress"][task] = False
            # Remove tasks not in roadmap
            for task in list(active["progress"].keys()):
                if task not in roadmap_tasks:
                    del active["progress"][task]
        return dict(active["progress"])
    return {}
