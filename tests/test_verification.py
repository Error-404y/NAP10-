import tempfile
import unittest
from pathlib import Path

from bot import Store, VoteButton, MIN_APPROVALS


class VerificationTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.directory.name) / "test.sqlite3")
        self.guild = 1
        self.applicant = 100

    def tearDown(self):
        self.store.close()
        self.directory.cleanup()

    def test_button_has_applicant_id(self):
        button = VoteButton(self.applicant)
        self.assertEqual(button.applicant_id, self.applicant)

    def test_three_unique_votes_and_retry(self):
        self.assertTrue(self.store.submit(self.guild, self.applicant, "Alliance", "Player"))
        self.assertEqual(self.store.vote(self.guild, self.applicant, 1), ("recorded", 1))
        self.assertEqual(self.store.vote(self.guild, self.applicant, 1), ("duplicate", 1))
        self.assertEqual(self.store.vote(self.guild, self.applicant, 2), ("recorded", 2))
        self.assertEqual(self.store.vote(self.guild, self.applicant, 3), ("ready", MIN_APPROVALS))
        self.assertEqual(self.store.vote(self.guild, self.applicant, 3), ("ready", MIN_APPROVALS))
        self.assertEqual(self.store.application(self.guild, self.applicant)["status"], "pending")
        self.store.mark_approved(self.guild, self.applicant)
        self.assertEqual(self.store.application(self.guild, self.applicant)["status"], "approved")
        self.assertEqual(self.store.vote(self.guild, self.applicant, 4), ("closed", 0))

    def test_cancel_and_resubmit(self):
        self.store.submit(self.guild, self.applicant, "Alliance", "Player")
        self.store.vote(self.guild, self.applicant, 10)
        self.store.cancel(self.guild, self.applicant)
        self.assertIsNone(self.store.application(self.guild, self.applicant))
        self.assertTrue(self.store.submit(self.guild, self.applicant, "Other", "OtherPlayer"))
        self.assertEqual(self.store.count(self.guild, self.applicant), 0)


if __name__ == "__main__":
    unittest.main()
