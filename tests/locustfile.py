from locust import HttpUser, task, between
import itertools

USER_POOL = itertools.cycle([1, 2, 3])

class GuestUser(HttpUser):
    weight = 1
    wait_time = between(4, 6)

    @task
    def get_products(self):
        self.client.get("/products", name="/products (Guest)")


class LoggedInUser(HttpUser):
    weight = 3
    wait_time = between(1, 2)

    def on_start(self):
        self.user_id = next(USER_POOL)
        self.headers = {"Authorization": f"Bearer mock_user_{self.user_id}"}

    @task
    def get_products(self):
        self.client.get(
            "/products",
            headers=self.headers,
            name="/products (Logged In)"
        )

"""
phase-1 under the limit 
guest: between(14, 16)
logged: between(3.5, 4)

phase-2 at limit
guest: between(11, 13)
logged: between(2.8, 3.2)

phase-3 over the limit
guest: between(4, 6)
logged: between(1, 2)

"""