from locust import HttpUser, task, between
import random
import string


def random_client():
    """Simulate 20 different clients hitting the API."""
    return f"client_{random.randint(1, 20)}"


class RateLimiterUser(HttpUser):
    wait_time = between(0.05, 0.2)

    @task(3)
    def hit_token_bucket(self):
        client_id = random_client()
        self.client.get(
            f"/api/token-bucket?client_id={client_id}",
            name="/api/token-bucket",
        )

    @task(3)
    def hit_sliding_window(self):
        client_id = random_client()
        self.client.get(
            f"/api/sliding-window?client_id={client_id}",
            name="/api/sliding-window",
        )

    @task(1)
    def health_check(self):
        self.client.get("/health", name="/health")