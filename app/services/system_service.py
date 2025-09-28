from app.utils.mikrotik_api import MikroTikAPI

class SystemService:
    def __init__(self):
        self.mikrotik_api = MikroTikAPI()

    def get_resources(self):
        return self.mikrotik_api.get_system_resources()
