import db
from config import default_delay, default_min_forward_rate


class UserSettings:
    def __init__(self, uid):
        settings = db.get_settings(uid)
        self.uid = uid
        self.delay = settings.get("delay", default_delay)
        self.min_forward_rate = settings.get("min_forward_rate", default_min_forward_rate)
        self.ai_enabled = bool(settings.get("ai_enabled", 0))
        self.system_prompt = settings.get("system_prompt", "")
