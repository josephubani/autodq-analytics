import tempfile
import unittest
from pathlib import Path

import pandas as pd

from app.autodq_web.auth import UserIdentity
from app.autodq_web.persistence import repository_for_url
from app.autodq_web.project_store import LocalObjectStore, StudioProjectService


class StreamlitProjectPersistenceTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        root = Path(self.temporary_directory.name)
        self.url = f"sqlite+pysqlite:///{root / 'studio.db'}"
        self.repository = repository_for_url(self.url)
        self.service = StudioProjectService(
            self.repository,
            LocalObjectStore(root / "objects"),
        )
        self.identity = UserIdentity(
            issuer="https://identity.example/",
            subject="user-1",
            display_name="Ada Analyst",
            email="ada@example.test",
        )
        self.context = self.repository.synchronize_identity(self.identity)
        self.workspace_id = self.context.personal_workspace.id
        self.frame = pd.DataFrame(
            {
                "Region": ["East", "West", "East"],
                "Revenue": [120.5, 80.0, 210.25],
            }
        )
        self.payload = self.frame.to_csv(index=False).encode("utf-8")

    def tearDown(self):
        self.repository.engine.dispose()
        repository_for_url.cache_clear()
        self.temporary_directory.cleanup()

    def test_upload_creates_project_dataset_and_restorable_raw_version(self):
        saved = self.service.save_upload(
            user_id=self.context.user_id,
            workspace_id=self.workspace_id,
            project_id=None,
            project_name="Sales analysis",
            dataset_name="sales",
            original_filename="sales.csv",
            payload=self.payload,
            frame=self.frame,
        )

        projects = self.service.list_projects(
            user_id=self.context.user_id,
            workspace_id=self.workspace_id,
        )
        self.assertEqual(len(projects), 1)
        self.assertEqual(projects[0].active_dataset_name, "sales")

        restored = self.service.restore_project(
            user_id=self.context.user_id,
            project_id=saved.project.id,
        )
        self.assertEqual(restored.raw_path.read_bytes(), self.payload)
        self.assertEqual(restored.stage_checksums, saved.stage_checksums)

    def test_cleaned_and_engineered_stages_round_trip_with_dtypes(self):
        saved = self.service.save_upload(
            user_id=self.context.user_id,
            workspace_id=self.workspace_id,
            project_id=None,
            project_name="Typed data",
            dataset_name="sales",
            original_filename="sales.csv",
            payload=self.payload,
            frame=self.frame,
        )
        cleaned = self.frame.assign(Revenue=self.frame["Revenue"].round(0))
        engineered = cleaned.assign(High_Value=cleaned["Revenue"] >= 100)

        first = self.service.save_stage(
            user_id=self.context.user_id,
            workspace_id=self.workspace_id,
            project_id=saved.project.id,
            dataset_id=saved.dataset_id,
            stage="cleaned",
            frame=cleaned,
            target_column="Revenue",
        )
        repeated = self.service.save_stage(
            user_id=self.context.user_id,
            workspace_id=self.workspace_id,
            project_id=saved.project.id,
            dataset_id=saved.dataset_id,
            stage="cleaned",
            frame=cleaned,
            target_column="Revenue",
        )
        self.service.save_stage(
            user_id=self.context.user_id,
            workspace_id=self.workspace_id,
            project_id=saved.project.id,
            dataset_id=saved.dataset_id,
            stage="engineered",
            frame=engineered,
            target_column="Revenue",
        )

        self.assertEqual(first.id, repeated.id)
        restored = self.service.restore_project(
            user_id=self.context.user_id,
            project_id=saved.project.id,
        )
        pd.testing.assert_frame_equal(restored.cleaned_data, cleaned)
        pd.testing.assert_frame_equal(restored.engineered_data, engineered)
        self.assertEqual(restored.target_column, "Revenue")

    def test_project_access_is_restricted_to_workspace_members(self):
        saved = self.service.save_upload(
            user_id=self.context.user_id,
            workspace_id=self.workspace_id,
            project_id=None,
            project_name="Private project",
            dataset_name="sales",
            original_filename="sales.csv",
            payload=self.payload,
            frame=self.frame,
        )
        outsider = self.repository.synchronize_identity(
            UserIdentity(
                issuer="https://identity.example/",
                subject="user-2",
                display_name="Grace Analyst",
                email="grace@example.test",
            )
        )

        with self.assertRaises(PermissionError):
            self.service.restore_project(
                user_id=outsider.user_id,
                project_id=saved.project.id,
            )

    def test_viewer_can_restore_a_named_dataset_without_mutating_the_project(self):
        workspace = self.repository.create_team_workspace(
            user_id=self.context.user_id,
            name="Shared analytics",
        )
        saved = self.service.save_upload(
            user_id=self.context.user_id,
            workspace_id=workspace.id,
            project_id=None,
            project_name="Shared sales",
            dataset_name="sales",
            original_filename="sales.csv",
            payload=self.payload,
            frame=self.frame,
        )
        self.repository.invite_workspace_member(
            user_id=self.context.user_id,
            workspace_id=workspace.id,
            email="viewer@example.test",
            role="viewer",
        )
        viewer = self.repository.synchronize_identity(
            UserIdentity(
                issuer="https://identity.example/",
                subject="viewer-1",
                display_name="Vera Viewer",
                email="viewer@example.test",
                email_verified=True,
            )
        )

        restored = self.service.restore_project(
            user_id=viewer.user_id,
            project_id=saved.project.id,
            dataset_id=saved.dataset_id,
        )

        self.assertEqual(restored.dataset_name, "sales")
        self.assertEqual(restored.raw_path.read_bytes(), self.payload)
        with self.assertRaises(PermissionError):
            self.service.save_stage(
                user_id=viewer.user_id,
                workspace_id=workspace.id,
                project_id=saved.project.id,
                dataset_id=saved.dataset_id,
                stage="cleaned",
                frame=self.frame,
                target_column=None,
            )

    def test_a_project_can_restore_each_named_dataset(self):
        first = self.service.save_upload(
            user_id=self.context.user_id,
            workspace_id=self.workspace_id,
            project_id=None,
            project_name="Customer analytics",
            dataset_name="sales",
            original_filename="sales.csv",
            payload=self.payload,
            frame=self.frame,
        )
        customers = pd.DataFrame(
            {"Customer": ["Ada", "Grace"], "Email": ["ada@test", "grace@test"]}
        )
        second = self.service.save_upload(
            user_id=self.context.user_id,
            workspace_id=self.workspace_id,
            project_id=first.project.id,
            project_name="Customer analytics",
            dataset_name="customers",
            original_filename="customers.csv",
            payload=customers.to_csv(index=False).encode("utf-8"),
            frame=customers,
        )

        datasets = self.service.list_datasets(
            user_id=self.context.user_id,
            project_id=first.project.id,
        )
        self.assertEqual({dataset.name for dataset in datasets}, {"sales", "customers"})

        restored = self.service.restore_project(
            user_id=self.context.user_id,
            project_id=first.project.id,
            dataset_id=first.dataset_id,
        )
        self.assertEqual(restored.dataset_name, "sales")
        self.assertEqual(restored.raw_path.read_bytes(), self.payload)

        projects = self.service.list_projects(
            user_id=self.context.user_id,
            workspace_id=self.workspace_id,
        )
        self.assertEqual(projects[0].active_dataset_id, first.dataset_id)
        self.assertNotEqual(first.dataset_id, second.dataset_id)

    def test_storage_prefix_must_match_the_projects_workspace(self):
        saved = self.service.save_upload(
            user_id=self.context.user_id,
            workspace_id=self.workspace_id,
            project_id=None,
            project_name="Protected storage",
            dataset_name="sales",
            original_filename="sales.csv",
            payload=self.payload,
            frame=self.frame,
        )

        with self.assertRaises(PermissionError):
            self.service.save_stage(
                user_id=self.context.user_id,
                workspace_id="wrong-workspace",
                project_id=saved.project.id,
                dataset_id=saved.dataset_id,
                stage="cleaned",
                frame=self.frame,
                target_column=None,
            )


if __name__ == "__main__":
    unittest.main()
