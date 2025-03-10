"""
Unit tests for resdk/resources/user.py file.
"""

import unittest

from mock import MagicMock

from resdk.resources.user import Group, User

from .utils import server_resource


class TestGroup(unittest.TestCase):
    def setUp(self):
        self.resolwe = MagicMock()
        self.user = server_resource(User, resolwe=self.resolwe, id=42)
        self.group = server_resource(
            Group, resolwe=self.resolwe, name="Test group", id=1
        )
        self.group_no_id = server_resource(
            Group, resolwe=self.resolwe, name="Test group"
        )

    def test_users_no_id(self):
        with self.assertRaises(ValueError):
            self.group_no_id.users

    def test_users(self):
        self.resolwe.user.filter.return_value = [self.user]
        users = self.group.users

        self.assertEqual(len(users), 1)
        self.assertEqual(users[0], self.user)

    def test_add_user_no_id(self):
        with self.assertRaises(ValueError):
            self.group_no_id.add_users(self.user)

    def test_add_user(self):
        self.group.add_users(self.user)
        self.resolwe.api.group().add_users.post.assert_called_with({"user_ids": [42]})

    def test_remove_user_no_id(self):
        with self.assertRaises(ValueError):
            self.group_no_id.remove_users(self.user)

    def test_remove_user(self):
        self.group.remove_users(self.user)
        self.resolwe.api.group().remove_users.post.assert_called_with(
            {"user_ids": [42]}
        )


if __name__ == "__main__":
    unittest.main()
