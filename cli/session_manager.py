import json
import os
from datetime import datetime

class SessionManager:
    def __init__(self, session_dir="browser_sessions"):
        self.session_dir = session_dir
        if not os.path.exists(session_dir):
            os.makedirs(session_dir)

    async def save_session(self, context, session_name):
        try:
            storage = await context.storage_state()
            storage['timestamp'] = datetime.now().isoformat()
            session_path = os.path.join(self.session_dir, f"{session_name}.json")
            with open(session_path, 'w', encoding='utf-8') as f:
                json.dump(storage, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving session: {str(e)}")
            return False

    def get_session_path(self, session_name):
        return os.path.join(self.session_dir, f"{session_name}.json")

    async def is_session_valid(self, session_name, max_age_hours=24):
        try:
            session_path = self.get_session_path(session_name)
            if not os.path.exists(session_path):
                return False
            with open(session_path, 'r', encoding='utf-8') as f:
                storage = json.load(f)
            if 'timestamp' not in storage:
                return False
            stored_time = datetime.fromisoformat(storage['timestamp'])
            age = datetime.now() - stored_time
            return age.total_seconds() < (max_age_hours * 3600)
        except Exception:
            return False
