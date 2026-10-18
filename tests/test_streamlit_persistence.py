import tempfile
import unittest
from pathlib import Path

from sqlalchemy import func, select

from app.autodq_web.auth import UserIdentity
from app.autodq_web.persistence import (
    UserRecord,
    WorkspaceMembershipRecord,
    WorkspaceRecord,
    database_url,
    repository_for_url,
)


class StreamlitPersistenceTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        database_path = Path(self.temporary_directory.name) / "studio.db"
        self.url = f"sqlite+pysqlite:///{database_path}"
        self.repository = repository_for_url(self.url)

    def tearDown(self):
        self.repository.engine.dispose()
        repository_for_url.cache_clear()
        self.temporary_directory.cleanup()

    def identity(self, *, subject="user-1", name="Ada Analyst", email="ada@example.test"):
        return UserIdentity(
            issuer="https://identity.example/",
            subject=subject,
            display_name=name,
            email=email,
        )

    def test_local_database_url_is_inside_the_studio_home(self):
        home = Path(self.temporary_directory.name) / "custom-home"
        url = database_url({}, default_home=home)
        self.assertEqual(url, f"sqlite+pysqlite:///{home.resolve() / 'studio.db'}")

    def test_first_login_creates_user_personal_workspace_and_owner_membership(self):
        context = self.repository.synchronize_identity(self.identity())

        self.assertEqual(len(context.workspaces), 1)
        workspace = context.personal_workspace
        self.assertEqual(workspace.name, "Ada Analyst's workspace")
        self.assertEqual(workspace.role, "owner")
        self.assertTrue(workspace.is_personal)

        with self.repository._sessions() as session:
            self.assertEqual(session.scalar(select(func.count()).select_from(UserRecord)), 1)
            self.assertEqual(
                session.scalar(select(func.count()).select_from(WorkspaceRecord)),
                1,
            )
            self.assertEqual(
                session.scalar(
                    select(func.count()).select_from(WorkspaceMembershipRecord)
                ),
                1,
            )

    def test_repeated_login_is_idempotent_and_refreshes_profile(self):
        first = self.repository.synchronize_identity(self.identity())
        second = self.repository.synchronize_identity(
            self.identity(name="Ada Lovelace", email="ada.lovelace@example.test")
        )

        self.assertEqual(first.user_id, second.user_id)
        self.assertEqual(first.personal_workspace.id, second.personal_workspace.id)
        with self.repository._sessions() as session:
            user = session.get(UserRecord, first.user_id)
            self.assertEqual(user.display_name, "Ada Lovelace")
            self.assertEqual(user.email, "ada.lovelace@example.test")
            self.assertEqual(session.scalar(select(func.count()).select_from(UserRecord)), 1)

    def test_users_receive_isolated_personal_workspaces(self):
        first = self.repository.synchronize_identity(self.identity(subject="user-1"))
        second = self.repository.synchronize_identity(
            self.identity(
                subject="user-2",
                name="Grace Analyst",
                email="grace@example.test",
            )
        )

        self.assertNotEqual(first.user_id, second.user_id)
        self.assertNotEqual(first.personal_workspace.id, second.personal_workspace.id)
        self.assertEqual(
            self.repository.identity_context(self.identity(subject="user-1")).workspaces,
            first.workspaces,
        )


if __name__ == "__main__":
    unittest.main()
