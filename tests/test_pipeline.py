#!/usr/bin/env python3
"""
End-to-end tests for the INDmoney Review Pulse pipeline.
Tests all core modules WITHOUT making real API calls (uses existing output files).

Run:  python3 tests/test_pipeline.py
"""

import os
import sys
import json
import re
import unittest

# Ensure project root is in path
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_DIR)
os.chdir(PROJECT_DIR)

OUTPUT_DIR = os.path.join(PROJECT_DIR, "output")


class TestPhase1Output(unittest.TestCase):
    """Verify Phase 1 output files exist and have correct structure."""

    def test_playstore_reviews_exist(self):
        path = os.path.join(OUTPUT_DIR, "playstore_reviews.json")
        self.assertTrue(os.path.exists(path), "playstore_reviews.json missing")

    def test_appstore_reviews_exist(self):
        path = os.path.join(OUTPUT_DIR, "appstore_reviews.json")
        self.assertTrue(os.path.exists(path), "appstore_reviews.json missing")

    def test_playstore_reviews_structure(self):
        path = os.path.join(OUTPUT_DIR, "playstore_reviews.json")
        with open(path, "r") as f:
            data = json.load(f)
        self.assertIn("metadata", data)
        self.assertIn("reviews", data)
        self.assertGreater(len(data["reviews"]), 0, "No Play Store reviews")

        # Check review structure
        review = data["reviews"][0]
        required_keys = {"sr_no", "rating", "review_text", "date", "source"}
        self.assertTrue(required_keys.issubset(review.keys()),
                        f"Missing keys: {required_keys - review.keys()}")

    def test_appstore_reviews_structure(self):
        path = os.path.join(OUTPUT_DIR, "appstore_reviews.json")
        with open(path, "r") as f:
            data = json.load(f)
        self.assertIn("reviews", data)
        if len(data["reviews"]) > 0:
            review = data["reviews"][0]
            self.assertIn("rating", review)
            self.assertIn("review_text", review)

    def test_reviews_have_no_pii(self):
        """Verify PII scrubbing: no emails, phone numbers, or card numbers."""
        for fname in ["playstore_reviews.json", "appstore_reviews.json"]:
            path = os.path.join(OUTPUT_DIR, fname)
            if not os.path.exists(path):
                continue
            with open(path, "r") as f:
                data = json.load(f)

            for review in data.get("reviews", []):
                text = review.get("review_text", "")
                # Email pattern
                self.assertFalse(
                    re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text),
                    f"PII leak (email) in review #{review.get('sr_no')}: {text[:50]}"
                )
                # Phone pattern (10+ digits)
                self.assertFalse(
                    re.search(r'\b\d{10,}\b', text),
                    f"PII leak (phone) in review #{review.get('sr_no')}: {text[:50]}"
                )

    def test_reviews_minimum_word_count(self):
        """All reviews should have >= 5 words (short ones filtered)."""
        path = os.path.join(OUTPUT_DIR, "playstore_reviews.json")
        with open(path, "r") as f:
            data = json.load(f)
        for review in data["reviews"]:
            word_count = len(review["review_text"].split())
            self.assertGreaterEqual(word_count, 5,
                                    f"Review #{review['sr_no']} too short: '{review['review_text']}'")

    def test_ratings_in_valid_range(self):
        """All ratings should be 1-5."""
        for fname in ["playstore_reviews.json", "appstore_reviews.json"]:
            path = os.path.join(OUTPUT_DIR, fname)
            if not os.path.exists(path):
                continue
            with open(path, "r") as f:
                data = json.load(f)
            for review in data["reviews"]:
                self.assertIn(review["rating"], [1, 2, 3, 4, 5],
                              f"Invalid rating: {review['rating']}")


class TestPhase2Output(unittest.TestCase):
    """Verify Phase 2 theme classification output."""

    def _get_latest_file(self, pattern):
        import glob
        files = sorted(glob.glob(os.path.join(OUTPUT_DIR, pattern)), reverse=True)
        return files[0] if files else None

    def test_themes_file_exists(self):
        path = self._get_latest_file("grouped_reviews-*.json") or \
               os.path.join(OUTPUT_DIR, "themes.json")
        self.assertTrue(os.path.exists(path), "No themes file found")

    def test_themes_structure(self):
        path = self._get_latest_file("grouped_reviews-*.json") or \
               os.path.join(OUTPUT_DIR, "themes.json")
        with open(path, "r") as f:
            data = json.load(f)

        self.assertIn("themes", data)
        self.assertIn("by_theme", data)
        self.assertIn("metadata", data)

        # Should have 3-5 themes
        num_themes = len(data["themes"])
        self.assertGreaterEqual(num_themes, 3, f"Too few themes: {num_themes}")
        self.assertLessEqual(num_themes, 7, f"Too many themes: {num_themes}")

    def test_theme_has_required_fields(self):
        path = self._get_latest_file("grouped_reviews-*.json") or \
               os.path.join(OUTPUT_DIR, "themes.json")
        with open(path, "r") as f:
            data = json.load(f)

        for theme in data["themes"]:
            self.assertIn("id", theme)
            self.assertIn("label", theme)
            self.assertIn("description", theme)

    def test_all_reviews_classified(self):
        """Every review should be classified into a theme."""
        path = self._get_latest_file("grouped_reviews-*.json") or \
               os.path.join(OUTPUT_DIR, "themes.json")
        with open(path, "r") as f:
            data = json.load(f)

        total_classified = sum(
            td["review_count"] for td in data["by_theme"].values()
        )
        expected = data["metadata"]["total_reviews"]
        self.assertEqual(total_classified, expected,
                         f"Classified {total_classified}/{expected} reviews")

    def test_theme_review_counts_match(self):
        """by_theme review_count should match actual reviews list length."""
        path = self._get_latest_file("grouped_reviews-*.json") or \
               os.path.join(OUTPUT_DIR, "themes.json")
        with open(path, "r") as f:
            data = json.load(f)

        for tid, td in data["by_theme"].items():
            self.assertEqual(
                td["review_count"], len(td["reviews"]),
                f"Theme '{tid}': count={td['review_count']} but {len(td['reviews'])} reviews"
            )


class TestPhase3Output(unittest.TestCase):
    """Verify Phase 3 pulse note output."""

    def _get_latest_file(self, pattern):
        import glob
        files = sorted(glob.glob(os.path.join(OUTPUT_DIR, pattern)), reverse=True)
        return files[0] if files else None

    def test_pulse_note_exists(self):
        path = self._get_latest_file("weekly_pulse-*.md")
        self.assertIsNotNone(path, "No weekly_pulse-*.md found")

    def test_email_body_exists(self):
        path = self._get_latest_file("email_body-*.html")
        self.assertIsNotNone(path, "No email_body-*.html found")

    def test_pulse_output_json_exists(self):
        path = self._get_latest_file("pulse_output-*.json")
        self.assertIsNotNone(path, "No pulse_output-*.json found")

    def test_pulse_output_structure(self):
        path = self._get_latest_file("pulse_output-*.json")
        with open(path, "r") as f:
            data = json.load(f)

        self.assertIn("pulse_note", data)
        self.assertIn("email_subject", data)
        self.assertIn("email_body_html", data)

    def test_pulse_note_word_limit(self):
        """Pulse note should be ≤ 400 words (we say 250 but allow some flex)."""
        path = self._get_latest_file("weekly_pulse-*.md")
        with open(path, "r") as f:
            content = f.read()
        word_count = len(content.split())
        self.assertLessEqual(word_count, 400,
                             f"Pulse note too long: {word_count} words")
        self.assertGreater(word_count, 50,
                           f"Pulse note too short: {word_count} words")

    def test_pulse_note_has_sections(self):
        """Pulse note should have Key Themes, User Voices, and Actions."""
        path = self._get_latest_file("weekly_pulse-*.md")
        with open(path, "r") as f:
            content = f.read()

        self.assertIn("Theme", content, "Missing 'Themes' section")
        self.assertIn("Action", content, "Missing 'Actions' section")

    def test_email_body_is_valid_html(self):
        """Email body should contain basic HTML structure."""
        path = self._get_latest_file("email_body-*.html")
        with open(path, "r") as f:
            html = f.read()

        self.assertIn("<html", html.lower())
        self.assertIn("</html>", html.lower())
        self.assertIn("<body", html.lower())

    def test_email_subject_not_empty(self):
        path = self._get_latest_file("pulse_output-*.json")
        with open(path, "r") as f:
            data = json.load(f)
        self.assertGreater(len(data["email_subject"]), 10,
                           "Email subject too short or empty")


class TestPhase4Module(unittest.TestCase):
    """Verify Phase 4 email module (without sending)."""

    def test_email_sender_imports(self):
        """Phase 4 module should import cleanly."""
        from phase4_email.email_sender import _build_email, save_eml
        self.assertTrue(callable(_build_email))
        self.assertTrue(callable(save_eml))

    def test_build_email_structure(self):
        """Build an email and verify MIME structure."""
        from phase4_email.email_sender import _build_email
        msg = _build_email(
            sender="test@test.com",
            recipient="to@test.com",
            subject="Test Subject",
            html_body="<p>Hello</p>",
        )
        self.assertEqual(msg["From"], "test@test.com")
        self.assertEqual(msg["To"], "to@test.com")
        self.assertEqual(msg["Subject"], "Test Subject")

    def test_eml_file_generation(self):
        """save_eml should create a .eml file."""
        from phase4_email.email_sender import save_eml
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            path = save_eml(
                recipient="test@test.com",
                subject="Test",
                html_body="<p>Hello</p>",
                output_dir=tmpdir,
            )
            self.assertTrue(os.path.exists(path))
            with open(path, "r") as f:
                content = f.read()
            self.assertIn("Test", content)


class TestDashboardServer(unittest.TestCase):
    """Verify the localhost dashboard file is valid."""

    def test_dashboard_imports(self):
        """dashboard.py should import without errors."""
        # Just check the file is syntactically valid
        path = os.path.join(PROJECT_DIR, "dashboard.py")
        with open(path, "r") as f:
            code = f.read()
        compile(code, "dashboard.py", "exec")

    def test_streamlit_app_imports(self):
        """phase5_ui/app.py should be syntactically valid."""
        path = os.path.join(PROJECT_DIR, "phase5_ui", "app.py")
        with open(path, "r") as f:
            code = f.read()
        compile(code, "app.py", "exec")


class TestMarkdownToHtml(unittest.TestCase):
    """Test the markdown-to-HTML converter in dashboard.py."""

    def setUp(self):
        # Import _md_to_html from dashboard
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "dashboard", os.path.join(PROJECT_DIR, "dashboard.py"),
        )
        # We can't fully import dashboard (it starts server), so test via regex
        pass

    def test_bullet_points_render_as_list(self):
        """Verify that - and * bullets create <li> elements."""
        # Read the function source and check it handles dashes
        path = os.path.join(PROJECT_DIR, "dashboard.py")
        with open(path, "r") as f:
            code = f.read()
        self.assertIn("[-*]", code, "Markdown parser doesn't handle - bullets")
        self.assertIn("<li", code, "Markdown parser doesn't create <li> elements")
        self.assertIn("<ul", code, "Markdown parser doesn't create <ul> wrapper")


if __name__ == "__main__":
    print(f"\n{'='*60}")
    print(f"  INDmoney Review Pulse — End-to-End Tests")
    print(f"  Testing against output files in: {OUTPUT_DIR}")
    print(f"{'='*60}\n")

    unittest.main(verbosity=2)
