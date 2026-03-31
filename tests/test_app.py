import tempfile
import unittest
from pathlib import Path

from software_system import create_app


class AccessControlAppTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        database_path = Path(self.temp_dir.name) / "test_access_control.db"

        self.app = create_app(
            {
                "TESTING": True,
                "SECRET_KEY": "test-secret",
                "DATABASE": str(database_path),
                "DEVICE_API_KEY": "test-device-key",
                "DEFAULT_ADMIN_USERNAME": "admin",
                "DEFAULT_ADMIN_PASSWORD": "test-password",
            }
        )
        self.client = self.app.test_client()

    def tearDown(self):
        self.temp_dir.cleanup()

    def login(self):
        return self.client.post(
            "/login",
            data={"username": "admin", "password": "test-password"},
            follow_redirects=True,
        )

    def test_unknown_scan_is_denied(self):
        response = self.client.post(
            "/api/scan",
            json={"rfid_uid": "11-22-33-44", "source": "raspberry_pi"},
            headers={"X-API-Key": "test-device-key"},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertFalse(payload["access_granted"])
        self.assertEqual(payload["status"], "denied")

    def test_registered_scan_is_granted_and_exported(self):
        login_response = self.login()
        self.assertEqual(login_response.status_code, 200)

        user_response = self.client.post(
            "/api/users",
            json={
                "name": "Murat Guvenc",
                "rfid_uid": "AA-BB-CC-DD",
                "role": "student",
                "is_active": True,
            },
        )
        self.assertEqual(user_response.status_code, 201)

        scan_response = self.client.post(
            "/api/scan",
            json={"rfid_uid": "AA-BB-CC-DD", "source": "raspberry_pi"},
            headers={"X-API-Key": "test-device-key"},
        )
        self.assertEqual(scan_response.status_code, 200)
        scan_payload = scan_response.get_json()
        self.assertTrue(scan_payload["access_granted"])
        self.assertEqual(scan_payload["status"], "granted")

        summary_response = self.client.get("/api/summary")
        self.assertEqual(summary_response.status_code, 200)
        summary = summary_response.get_json()
        self.assertEqual(summary["total_users"], 1)
        self.assertEqual(summary["granted_today"], 1)

        export_response = self.client.get("/export/attendance.csv")
        self.assertEqual(export_response.status_code, 200)
        export_text = export_response.get_data(as_text=True)
        self.assertIn("Murat Guvenc", export_text)
        self.assertIn("AA-BB-CC-DD", export_text)

    def test_duplicate_scan_is_not_logged_twice(self):
        self.login()
        self.client.post(
            "/api/users",
            json={
                "name": "Test User",
                "rfid_uid": "10-20-30-40",
                "role": "student",
                "is_active": True,
            },
        )

        first_scan = self.client.post(
            "/api/scan",
            json={"rfid_uid": "10-20-30-40", "source": "raspberry_pi"},
            headers={"X-API-Key": "test-device-key"},
        )
        second_scan = self.client.post(
            "/api/scan",
            json={"rfid_uid": "10-20-30-40", "source": "raspberry_pi"},
            headers={"X-API-Key": "test-device-key"},
        )

        self.assertEqual(first_scan.status_code, 200)
        self.assertEqual(second_scan.status_code, 200)
        self.assertTrue(first_scan.get_json()["logged"])
        self.assertFalse(second_scan.get_json()["logged"])
        self.assertTrue(second_scan.get_json()["duplicate_scan"])

        summary_response = self.client.get("/api/summary")
        summary = summary_response.get_json()
        self.assertEqual(summary["granted_today"], 1)


if __name__ == "__main__":
    unittest.main()
