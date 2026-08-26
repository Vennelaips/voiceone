import unittest
from datetime import datetime, date
import json
import sys
import os

# Add parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app
from database import get_db
from services.crypto import hash_aadhaar, is_eligible_citizen, sanitize_aadhaar, is_valid_aadhaar_format
from services.moderation import CivicModerationService

class TestVoiceOneBackend(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config["TESTING"] = True
        self.app.config["SECRET_KEY"] = "test-secret-key"
        self.client = self.app.test_client()
        self.db = get_db()

    def test_aadhaar_sanitization_and_validation(self):
        self.assertEqual(sanitize_aadhaar("1234 5678 9012"), "123456789012")
        self.assertEqual(sanitize_aadhaar("1234-5678-9012"), "123456789012")
        self.assertTrue(is_valid_aadhaar_format("123456789012"))
        self.assertFalse(is_valid_aadhaar_format("12345"))
        self.assertFalse(is_valid_aadhaar_format("12345678901A"))

    def test_aadhaar_hashing_zero_plaintext_retention(self):
        raw_aadhaar = "987654321098"
        h1 = hash_aadhaar(raw_aadhaar)
        h2 = hash_aadhaar(raw_aadhaar)
        
        # Must be deterministic for voter deduplication
        self.assertEqual(h1, h2)
        # Must NOT contain any part of original 12 digits
        self.assertTrue(h1.startswith("citizen_v_"))
        self.assertNotIn(raw_aadhaar, h1)

    def test_age_verification_eligibility(self):
        # 18+ Citizen
        eligible, age, msg = is_eligible_citizen("2000-01-01")
        self.assertTrue(eligible)
        self.assertGreaterEqual(age, 18)

        # Underage (< 18) Citizen
        underage_year = date.today().year - 15
        eligible_minor, age_minor, msg_minor = is_eligible_citizen(f"{underage_year}-05-10")
        self.assertFalse(eligible_minor)
        self.assertLess(age_minor, 18)
        self.assertIn("Access restricted", msg_minor)

    def test_civic_moderation_engine(self):
        # Polite post -> Approved
        res_approved = CivicModerationService.evaluate_text("This amendment creates a well-balanced framework for public health.")
        self.assertTrue(res_approved["is_approved"])
        self.assertEqual(res_approved["status"], "APPROVED")

        # Caste/Class discrimination -> Blocked & Auto-Removed
        res_caste = CivicModerationService.evaluate_text("These untouchable low caste people do not deserve benefits.")
        self.assertFalse(res_caste["is_approved"])
        self.assertEqual(res_caste["status"], "REMOVED")
        self.assertIn("CASTE_OR_CLASS_DISCRIMINATION", res_caste["violations"])

        # Religious Hatred -> Blocked
        res_religion = CivicModerationService.evaluate_text("Hate all muslims and ban their places.")
        self.assertFalse(res_religion["is_approved"])
        self.assertEqual(res_religion["status"], "REMOVED")
        self.assertIn("RELIGIOUS_HATRED", res_religion["violations"])

        # Gender/Orientation discrimination -> Blocked
        res_gender = CivicModerationService.evaluate_text("Women belong in kitchen and should not vote.")
        self.assertFalse(res_gender["is_approved"])
        self.assertEqual(res_gender["status"], "REMOVED")

    def test_api_auth_verify_endpoint(self):
        # Successful 18+ Verification
        resp = self.client.post("/api/auth/verify", json={
            "name": "Kavya Patel",
            "aadhaar": "987654321012",
            "dob": "1995-08-20"
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["success"])
        self.assertTrue(data["citizen_hash"].startswith("citizen_v_"))

        # Underage Rejection
        resp_minor = self.client.post("/api/auth/verify", json={
            "name": "Minor User",
            "aadhaar": "987654321012",
            "dob": "2015-08-20"
        })
        self.assertEqual(resp_minor.status_code, 403)
        data_minor = resp_minor.get_json()
        self.assertFalse(data_minor["success"])

    def test_api_voting_flow(self):
        # Create a test poll
        create_resp = self.client.post("/api/polls", json={
            "title": "Clean Water Infrastructure Bill 2026",
            "summary": "Mandates potable water pipelines across all municipal zones.",
            "official_source_url": "https://prsindia.org/clean-water-2026",
            "category": "Healthcare & Welfare"
        })
        self.assertEqual(create_resp.status_code, 201)
        poll_id = create_resp.get_json()["poll_id"]

        # Vote FOR
        vote_resp = self.client.post(f"/api/polls/{poll_id}/vote", json={
            "choice": "FOR",
            "citizen_hash": "citizen_v_voter_alpha"
        })
        self.assertEqual(vote_resp.status_code, 200)
        self.assertEqual(vote_resp.get_json()["votes_for"], 1)

        # Update vote to AGAINST
        vote_update = self.client.post(f"/api/polls/{poll_id}/vote", json={
            "choice": "AGAINST",
            "citizen_hash": "citizen_v_voter_alpha"
        })
        self.assertEqual(vote_update.status_code, 200)
        self.assertEqual(vote_update.get_json()["votes_for"], 0)
        self.assertEqual(vote_update.get_json()["votes_against"], 1)

    def test_api_forum_auto_moderation(self):
        # Valid post
        resp_ok = self.client.post("/api/forum/post", json={
            "content": "A thoughtful proposal that addresses real community needs.",
            "author_name": "Rohan Das",
            "citizen_hash": "citizen_v_rohan"
        })
        self.assertEqual(resp_ok.status_code, 201)
        self.assertEqual(resp_ok.get_json()["status"], "APPROVED")

        # Prohibited post
        resp_bad = self.client.post("/api/forum/post", json={
            "content": "These casteist people are lower class filth and should be banned.",
            "author_name": "Abusive User",
            "citizen_hash": "citizen_v_abuser"
        })
        self.assertEqual(resp_bad.status_code, 422)
        self.assertEqual(resp_bad.get_json()["status"], "REMOVED")

if __name__ == "__main__":
    unittest.main()
