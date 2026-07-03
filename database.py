import time
from typing import Optional, Dict, List

class DynamicStore:
    def __init__(self):
        self.pending_commands: List[dict] = []
        self.active_requests: List[dict] = []
        self.imei_to_user: Dict[str, int] = {}
        self.user_history: Dict[int, List[float]] = {}
        self.logs = []

    def check_and_update_limit(self, user_id: int, max_limits: int = 5) -> tuple[bool, int]:
        current_time = time.time()
        one_day_ago = current_time - (24 * 3600)
        if user_id not in self.user_history:
            self.user_history[user_id] = []
        self.user_history[user_id] = [t for t in self.user_history[user_id] if t > one_day_ago]
        if len(self.user_history[user_id]) >= max_limits:
            return False, 0
        self.user_history[user_id].append(current_time)
        return True, max_limits - len(self.user_history[user_id])

    def add_command(self, imei: str, user_id: int) -> bool:
        if imei in self.imei_to_user: return False
        self.pending_commands.append({"imei": imei, "user_id": user_id})
        self.imei_to_user[imei] = user_id
        self.log(f"User {user_id} ne IMEI {imei} request kiya.")
        return True

    def get_pending_command(self) -> Optional[dict]:
        if self.pending_commands:
            cmd = self.pending_commands.pop(0)
            self.active_requests.append(cmd)
            return cmd
        return None

    def pop_user_by_imei(self, imei: str) -> Optional[int]:
        for i, req in enumerate(self.active_requests):
            if req["imei"] == imei:
                self.active_requests.pop(i)
                return req["user_id"]
        return self.imei_to_user.get(imei)

    def pop_latest_active_user(self) -> Optional[dict]:
        if self.active_requests: return self.active_requests.pop(-1)
        return None

    def log(self, message: str):
        self.logs.append(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {message}")

store = DynamicStore()
