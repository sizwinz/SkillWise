import os
import json
import hashlib
from datetime import datetime
from typing import List, Dict, Any, Optional

def roadmap_id(resume: str, goal: str, role: str, salt: str = "") -> str:
    """Generate a stable 16-character hash identifying a roadmap configuration."""
    base = (resume.strip() + goal.strip() + role.strip() + salt.strip()).encode("utf-8")
    return hashlib.sha256(base).hexdigest()[:16]

def load_roadmaps_db(db_path: str) -> List[Dict[str, Any]]:
    """Safely load roadmap database with corruption protection."""
    if os.path.exists(db_path):
        try:
            with open(db_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
        except Exception:
            # Backup corrupted file if possible
            try:
                backup_path = f"{db_path}.corrupted_{int(datetime.now().timestamp())}"
                os.rename(db_path, backup_path)
            except Exception:
                pass
            return []
    return []

def save_roadmaps_db(roadmaps: List[Dict[str, Any]], db_path: str) -> bool:
    """Persist roadmaps database safely with UTF-8 encoding."""
    try:
        dirname = os.path.dirname(db_path)
        if dirname and not os.path.exists(dirname):
            os.makedirs(dirname, exist_ok=True)
            
        temp_path = f"{db_path}.tmp"
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(roadmaps, f, indent=2, ensure_ascii=False)
            
        # Atomic replace on POSIX / safe overwrite on Windows
        if os.path.exists(db_path):
            os.remove(db_path)
        os.rename(temp_path, db_path)
        return True
    except Exception as e:
        # Fallback direct write
        try:
            with open(db_path, "w", encoding="utf-8") as f:
                json.dump(roadmaps, f, indent=2, ensure_ascii=False)
            return True
        except Exception:
            return False

def get_active_roadmap(roadmaps_db: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Return the currently marked active roadmap or the first roadmap if none marked."""
    for r in roadmaps_db:
        if r.get("active"):
            return r
    if roadmaps_db:
        roadmaps_db[0]["active"] = True
        return roadmaps_db[0]
    return None

def set_active_roadmap(roadmaps_db: List[Dict[str, Any]], target_id: str) -> Optional[Dict[str, Any]]:
    """Set the specified roadmap as active and update its last_accessed timestamp."""
    active_item = None
    for r in roadmaps_db:
        if r.get("id") == target_id:
            r["active"] = True
            r["last_accessed"] = datetime.now().isoformat()
            active_item = r
        else:
            r["active"] = False
    return active_item

def sync_progress_from_active_roadmap(roadmaps_db: List[Dict[str, Any]], extract_roadmap_tasks_func) -> Dict[str, bool]:
    """Synchronize task progress checklist while preserving user completion records."""
    active = get_active_roadmap(roadmaps_db)
    if active is not None and "roadmap" in active:
        roadmap_tasks = extract_roadmap_tasks_func(active["roadmap"])
        if "progress" not in active or not isinstance(active["progress"], dict):
            active["progress"] = {task: False for task in roadmap_tasks}
        else:
            # Add newly discovered tasks
            for task in roadmap_tasks:
                if task not in active["progress"]:
                    active["progress"][task] = False
            # Retain historical progress while ensuring active tasks exist
        return dict(active["progress"])
    return {}
