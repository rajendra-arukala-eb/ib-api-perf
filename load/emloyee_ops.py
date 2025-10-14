from locust import HttpUser

class ApiUserBase(HttpUser):
    wait_time = lambda self: 0
    def on_start(self):
        self.login_v1(); self.login_v2()
    # put your _login_v1/_login_v2/_maybe_refresh_tokens here