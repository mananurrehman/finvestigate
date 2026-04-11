class TestPublicRoutes:
    def test_home_page(self, client):
        response = client.get("/")
        assert response.status_code == 200

    def test_login_page(self, client):
        response = client.get("/login")
        assert response.status_code == 200

    def test_signup_page(self, client):
        response = client.get("/signup")
        assert response.status_code == 200

class TestAuthProtection:
    def test_dashboard_requires_login(self, client):
        response = client.get("/dashboard")
        assert response.status_code == 302

    def test_transactions_requires_login(self, client):
        response = client.get("/transactions")
        assert response.status_code == 302