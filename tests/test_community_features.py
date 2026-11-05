import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from bot import MIN_APPROVALS, Store


class CommunityFeatureTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.directory.name) / "community.sqlite3")
        self.guild = 1565084541289369690

    def tearDown(self):
        self.store.close()
        self.directory.cleanup()

    def test_verification_requires_two_approvals(self):
        self.assertEqual(MIN_APPROVALS, 2)

    def test_announcement_schedule_persists(self):
        now = int(datetime.now(timezone.utc).timestamp())
        item = self.store.create_announcement(self.guild, 123, "Title", "Body", None, now - 1)
        self.assertIn(item, [row["id"] for row in self.store.due_announcements()])
        self.store.mark_announcement_sent(item, 555)
        self.assertNotIn(item, [row["id"] for row in self.store.due_announcements()])

    def test_poll_votes_are_unique_and_changeable(self):
        deadline = int(datetime.now(timezone.utc).timestamp()) + 3600
        self.store.create_poll(987, self.guild, 111, "Question?", ["First", "Second", "Third"], True, deadline)
        self.assertEqual(self.store.cast_poll_vote(987, 101, 0), "recorded")
        self.assertEqual(self.store.cast_poll_vote(987, 101, 1), "changed")
        self.assertEqual(self.store.cast_poll_vote(987, 202, 1), "recorded")
        self.assertEqual(self.store.poll_tallies(987), {1: 2})
        self.assertEqual(self.store.cast_poll_vote(987, 303, 5), "invalid")

    def test_expired_poll_cannot_accept_votes(self):
        deadline = int(datetime.now(timezone.utc).timestamp()) - 1
        self.store.create_poll(988, self.guild, 111, "Question?", ["Yes", "No"], True, deadline)
        self.assertEqual(self.store.cast_poll_vote(988, 101, 0), "closed")
        self.assertEqual(self.store.close_poll(988)["state"], "closed")


if __name__ == "__main__":
    unittest.main()
