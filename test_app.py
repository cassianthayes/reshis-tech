import tempfile
import unittest
from pathlib import Path

from app import app


class AppTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        old_config = {key: app.config[key] for key in ("DATABASE", "TESTING")}
        self.addCleanup(app.config.update, old_config)
        app.config.update(TESTING=True, DATABASE=Path(self.temp.name) / "users.sqlite3")
        self.client = app.test_client()
        self.account = {"username": "a", "password": "1"}

    def test_page(self):
        response = self.client.get("/login")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Войти", response.get_data(as_text=True))

    def test_auth(self):
        response = self.client.post("/register", data=self.account, follow_redirects=True)
        self.assertIn("Посчитать", response.get_data(as_text=True))
        self.client.post("/logout")
        self.assertEqual(self.client.get("/").status_code, 302)
        response = self.client.post("/login", data=self.account, follow_redirects=True)
        self.assertIn("Посчитать", response.get_data(as_text=True))

    def test_forecast(self):
        self.client.post("/register", data=self.account)
        response = self.client.post("/", data={"route": "MOW-AER", "date": "2026-06-01", "price": "10000"})
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("Спрос: 690.0", html)
        self.assertIn("Ожидаемые продажи: 690.0", html)
        self.assertIn('<canvas id="chart"', html)


if __name__ == "__main__":
    unittest.main()
