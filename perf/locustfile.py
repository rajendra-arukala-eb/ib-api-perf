from locust import events
from perf.config import CFG
from users.v1_user import V1ReadsUser
from users.v2_user import V2WritesUser

# Locust will auto-discover V1ReadsUser and V2WritesUser on import.

@events.init.add_listener
def _(environment, **kwargs):
    if not environment.host:
        environment.host = CFG["service"]["rest_v1_base_url"]
