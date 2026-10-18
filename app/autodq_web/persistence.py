"""Durable identity and workspace storage for AutoDQ Studio."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from uuid import UUID, uuid4, uuid5

from alembic import command
from alembic.config import Config
from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    create_engine,
    event,
    select,
)
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from app.autodq_web.auth import UserIdentity


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_STUDIO_HOME = REPOSITORY_ROOT / ".autodq-studio"
MIGRATION_CONFIG = REPOSITORY_ROOT / "app" / "alembic.ini"
MIGRATION_DIRECTORY = Path(__file__).resolve().parent / "migrations"

USER_NAMESPACE = UUID("6f83d45a-79c4-5e07-b808-11614ed6cd52")
WORKSPACE_NAMESPACE = UUID("59c61e8c-2b5a-5a74-b3af-ac926c0c66ee")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    """Base class shared by Studio's SQLAlchemy models and migrations."""


class UserRecord(Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("auth_issuer", "auth_subject", name="uq_users_identity"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    auth_issuer: Mapped[str] = mapped_column(String(500), nullable=False)
    auth_subject: Mapped[str] = mapped_column(String(500), nullable=False)
    email: Mapped[str | None] = mapped_column(String(320))
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    picture_url: Mapped[str | None] = mapped_column(String(2048))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    last_login_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )


class WorkspaceRecord(Base):
    __tablename__ = "workspaces"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    owner_user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    is_personal: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )


class WorkspaceMembershipRecord(Base):
    __tablename__ = "workspace_memberships"
    __table_args__ = (
        CheckConstraint(
            "role IN ('owner', 'editor', 'reviewer', 'viewer')",
            name="ck_workspace_memberships_role",
        ),
    )

    workspace_id: Mapped[str] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True, index=True
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )


class ProjectRecord(Base):
    __tablename__ = "projects"
    __table_args__ = (
        UniqueConstraint("workspace_id", "name", name="uq_projects_workspace_name"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(2000))
    active_dataset_id: Mapped[str | None] = mapped_column(String(36))
    created_by: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )


class DatasetRecord(Base):
    __tablename__ = "datasets"
    __table_args__ = (
        UniqueConstraint("project_id", "name", name="uq_datasets_project_name"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    target_column: Mapped[str | None] = mapped_column(String(255))
    created_by: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )


class DatasetVersionRecord(Base):
    __tablename__ = "dataset_versions"
    __table_args__ = (
        UniqueConstraint(
            "dataset_id",
            "stage",
            "version_number",
            name="uq_dataset_versions_stage_number",
        ),
        CheckConstraint(
            "stage IN ('raw', 'current', 'cleaned', 'engineered')",
            name="ck_dataset_versions_stage",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    dataset_id: Mapped[str] = mapped_column(
        ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    parent_version_id: Mapped[str | None] = mapped_column(
        ForeignKey("dataset_versions.id", ondelete="SET NULL")
    )
    stage: Mapped[str] = mapped_column(String(20), nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    storage_key: Mapped[str] = mapped_column(String(2048), nullable=False)
    file_format: Mapped[str] = mapped_column(String(20), nullable=False)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    row_count: Mapped[int] = mapped_column(BigInteger, nullable=False)
    column_count: Mapped[int] = mapped_column(Integer, nullable=False)
    created_by: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )


@dataclass(frozen=True)
class WorkspaceSummary:
    id: str
    name: str
    role: str
    is_personal: bool


@dataclass(frozen=True)
class IdentityContext:
    user_id: str
    identity_key: str
    workspaces: tuple[WorkspaceSummary, ...]

    @property
    def personal_workspace(self) -> WorkspaceSummary:
        for workspace in self.workspaces:
            if workspace.is_personal:
                return workspace
        raise LookupError("The user does not have a personal workspace.")


@dataclass(frozen=True)
class ProjectSummary:
    id: str
    workspace_id: str
    name: str
    description: str | None
    active_dataset_id: str | None
    active_dataset_name: str | None
    updated_at: datetime


@dataclass(frozen=True)
class DatasetSummary:
    id: str
    project_id: str
    name: str
    original_filename: str
    target_column: str | None
    updated_at: datetime


@dataclass(frozen=True)
class DatasetVersionSummary:
    id: str
    dataset_id: str
    stage: str
    version_number: int
    storage_key: str
    file_format: str
    checksum: str
    row_count: int
    column_count: int
    created_at: datetime


@dataclass(frozen=True)
class DatasetSnapshotMetadata:
    project: ProjectSummary
    dataset_id: str
    dataset_name: str
    original_filename: str
    target_column: str | None
    versions: dict[str, DatasetVersionSummary]


def database_url(
    environ: Mapping[str, str] | None = None,
    *,
    default_home: Path | None = None,
) -> str:
    """Return the configured database URL or the local SQLite default."""

    values = os.environ if environ is None else environ
    configured = values.get("AUTODQ_DATABASE_URL", "").strip()
    if configured:
        return configured

    home_value = values.get("AUTODQ_STUDIO_HOME", "").strip()
    home = Path(home_value).expanduser() if home_value else default_home
    home = (home or DEFAULT_STUDIO_HOME).resolve()
    return f"sqlite+pysqlite:///{home / 'studio.db'}"


def _prepare_database_location(url: str) -> None:
    parsed = make_url(url)
    if parsed.get_backend_name() != "sqlite" or parsed.database in {None, ":memory:"}:
        return
    Path(parsed.database).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)


def _enable_sqlite_foreign_keys(engine: Engine) -> None:
    if engine.url.get_backend_name() != "sqlite":
        return

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def create_database_engine(url: str) -> Engine:
    """Create an engine suitable for Streamlit's multi-session execution."""

    _prepare_database_location(url)
    connect_args = (
        {"check_same_thread": False}
        if make_url(url).get_backend_name() == "sqlite"
        else {}
    )
    engine = create_engine(url, pool_pre_ping=True, connect_args=connect_args)
    _enable_sqlite_foreign_keys(engine)
    return engine


def upgrade_database(url: str) -> None:
    """Upgrade the configured database to the latest Studio schema."""

    _prepare_database_location(url)
    config = Config(str(MIGRATION_CONFIG))
    config.set_main_option("script_location", str(MIGRATION_DIRECTORY))
    config.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
    command.upgrade(config, "head")


class StudioRepository:
    """Persistence boundary used by the Streamlit user interface."""

    def __init__(self, url: str) -> None:
        upgrade_database(url)
        self.engine = create_database_engine(url)
        self._sessions = sessionmaker(
            bind=self.engine,
            expire_on_commit=False,
            class_=Session,
        )

    def synchronize_identity(self, identity: UserIdentity) -> IdentityContext:
        """Upsert a user and guarantee exactly one deterministic personal workspace."""

        user_id = str(uuid5(USER_NAMESPACE, identity.identity_key))
        workspace_id = str(uuid5(WORKSPACE_NAMESPACE, f"personal:{user_id}"))
        now = utc_now()

        with self._sessions.begin() as session:
            user = session.get(UserRecord, user_id)
            if user is None:
                user = UserRecord(
                    id=user_id,
                    auth_issuer=identity.issuer,
                    auth_subject=identity.subject,
                    email=identity.email,
                    display_name=identity.display_name,
                    picture_url=identity.picture_url,
                    created_at=now,
                    last_login_at=now,
                )
                session.add(user)
            else:
                user.email = identity.email
                user.display_name = identity.display_name
                user.picture_url = identity.picture_url
                user.last_login_at = now

            workspace = session.get(WorkspaceRecord, workspace_id)
            if workspace is None:
                workspace = WorkspaceRecord(
                    id=workspace_id,
                    name=f"{identity.display_name}'s workspace",
                    owner_user_id=user_id,
                    is_personal=True,
                    created_at=now,
                    updated_at=now,
                )
                session.add(workspace)

            membership_key = {
                "workspace_id": workspace_id,
                "user_id": user_id,
            }
            membership = session.get(WorkspaceMembershipRecord, membership_key)
            if membership is None:
                session.add(
                    WorkspaceMembershipRecord(
                        workspace_id=workspace_id,
                        user_id=user_id,
                        role="owner",
                        joined_at=now,
                    )
                )

        return self.identity_context(identity)

    def identity_context(self, identity: UserIdentity) -> IdentityContext:
        user_id = str(uuid5(USER_NAMESPACE, identity.identity_key))
        with self._sessions() as session:
            rows = session.execute(
                select(WorkspaceRecord, WorkspaceMembershipRecord.role)
                .join(
                    WorkspaceMembershipRecord,
                    WorkspaceMembershipRecord.workspace_id == WorkspaceRecord.id,
                )
                .where(WorkspaceMembershipRecord.user_id == user_id)
                .order_by(WorkspaceRecord.is_personal.desc(), WorkspaceRecord.name)
            ).all()

        workspaces = tuple(
            WorkspaceSummary(
                id=workspace.id,
                name=workspace.name,
                role=role,
                is_personal=workspace.is_personal,
            )
            for workspace, role in rows
        )
        return IdentityContext(
            user_id=user_id,
            identity_key=identity.identity_key,
            workspaces=workspaces,
        )

    def _workspace_role(
        self,
        session: Session,
        *,
        user_id: str,
        workspace_id: str,
    ) -> str | None:
        return session.scalar(
            select(WorkspaceMembershipRecord.role).where(
                WorkspaceMembershipRecord.user_id == user_id,
                WorkspaceMembershipRecord.workspace_id == workspace_id,
            )
        )

    def _require_workspace_access(
        self,
        session: Session,
        *,
        user_id: str,
        workspace_id: str,
        write: bool = False,
    ) -> str:
        role = self._workspace_role(
            session,
            user_id=user_id,
            workspace_id=workspace_id,
        )
        if role is None:
            raise PermissionError("The user cannot access this workspace.")
        if write and role not in {"owner", "editor"}:
            raise PermissionError("The user cannot modify this workspace.")
        return role

    @staticmethod
    def _project_summary(session: Session, project: ProjectRecord) -> ProjectSummary:
        dataset_name = None
        if project.active_dataset_id:
            dataset = session.get(DatasetRecord, project.active_dataset_id)
            dataset_name = dataset.name if dataset is not None else None
        return ProjectSummary(
            id=project.id,
            workspace_id=project.workspace_id,
            name=project.name,
            description=project.description,
            active_dataset_id=project.active_dataset_id,
            active_dataset_name=dataset_name,
            updated_at=project.updated_at,
        )

    def list_projects(self, *, user_id: str, workspace_id: str) -> tuple[ProjectSummary, ...]:
        with self._sessions() as session:
            self._require_workspace_access(
                session,
                user_id=user_id,
                workspace_id=workspace_id,
            )
            projects = session.scalars(
                select(ProjectRecord)
                .where(ProjectRecord.workspace_id == workspace_id)
                .order_by(ProjectRecord.updated_at.desc(), ProjectRecord.name)
            ).all()
            return tuple(self._project_summary(session, project) for project in projects)

    def create_project(
        self,
        *,
        user_id: str,
        workspace_id: str,
        name: str,
        description: str | None = None,
    ) -> ProjectSummary:
        base_name = " ".join(name.split()).strip() or "Untitled project"
        base_name = base_name[:255]
        now = utc_now()
        with self._sessions.begin() as session:
            self._require_workspace_access(
                session,
                user_id=user_id,
                workspace_id=workspace_id,
                write=True,
            )
            existing_names = set(
                session.scalars(
                    select(ProjectRecord.name).where(
                        ProjectRecord.workspace_id == workspace_id
                    )
                )
            )
            candidate = base_name
            suffix = 2
            while candidate in existing_names:
                marker = f" ({suffix})"
                candidate = f"{base_name[: 255 - len(marker)]}{marker}"
                suffix += 1

            project = ProjectRecord(
                id=str(uuid4()),
                workspace_id=workspace_id,
                name=candidate,
                description=(description or "").strip() or None,
                active_dataset_id=None,
                created_by=user_id,
                created_at=now,
                updated_at=now,
            )
            session.add(project)
            session.flush()
            return self._project_summary(session, project)

    def create_dataset(
        self,
        *,
        user_id: str,
        project_id: str,
        name: str,
        original_filename: str,
        target_column: str | None = None,
    ) -> DatasetRecord:
        now = utc_now()
        base_name = " ".join(name.split()).strip() or "Dataset"
        base_name = base_name[:255]
        with self._sessions.begin() as session:
            project = session.get(ProjectRecord, project_id)
            if project is None:
                raise LookupError("Project not found.")
            self._require_workspace_access(
                session,
                user_id=user_id,
                workspace_id=project.workspace_id,
                write=True,
            )
            existing_names = set(
                session.scalars(
                    select(DatasetRecord.name).where(
                        DatasetRecord.project_id == project_id
                    )
                )
            )
            candidate = base_name
            suffix = 2
            while candidate in existing_names:
                marker = f" ({suffix})"
                candidate = f"{base_name[: 255 - len(marker)]}{marker}"
                suffix += 1

            dataset = DatasetRecord(
                id=str(uuid4()),
                project_id=project_id,
                name=candidate,
                original_filename=original_filename[:255],
                target_column=target_column,
                created_by=user_id,
                created_at=now,
                updated_at=now,
            )
            session.add(dataset)
            session.flush()
            project.active_dataset_id = dataset.id
            project.updated_at = now
            session.flush()
            return dataset

    @staticmethod
    def _dataset_summary(dataset: DatasetRecord) -> DatasetSummary:
        return DatasetSummary(
            id=dataset.id,
            project_id=dataset.project_id,
            name=dataset.name,
            original_filename=dataset.original_filename,
            target_column=dataset.target_column,
            updated_at=dataset.updated_at,
        )

    def list_datasets(
        self,
        *,
        user_id: str,
        project_id: str,
    ) -> tuple[DatasetSummary, ...]:
        with self._sessions() as session:
            project = session.get(ProjectRecord, project_id)
            if project is None:
                raise LookupError("Project not found.")
            self._require_workspace_access(
                session,
                user_id=user_id,
                workspace_id=project.workspace_id,
            )
            datasets = session.scalars(
                select(DatasetRecord)
                .where(DatasetRecord.project_id == project_id)
                .order_by(DatasetRecord.updated_at.desc(), DatasetRecord.name)
            ).all()
            return tuple(self._dataset_summary(dataset) for dataset in datasets)

    def activate_dataset(
        self,
        *,
        user_id: str,
        project_id: str,
        dataset_id: str,
    ) -> None:
        with self._sessions.begin() as session:
            project = session.get(ProjectRecord, project_id)
            if project is None:
                raise LookupError("Project not found.")
            self._require_workspace_access(
                session,
                user_id=user_id,
                workspace_id=project.workspace_id,
                write=True,
            )
            dataset = session.get(DatasetRecord, dataset_id)
            if dataset is None or dataset.project_id != project_id:
                raise LookupError("Dataset not found in this project.")
            project.active_dataset_id = dataset_id
            project.updated_at = utc_now()

    def update_dataset_target(
        self,
        *,
        user_id: str,
        dataset_id: str,
        target_column: str | None,
    ) -> None:
        with self._sessions.begin() as session:
            dataset = session.get(DatasetRecord, dataset_id)
            if dataset is None:
                raise LookupError("Dataset not found.")
            project = session.get(ProjectRecord, dataset.project_id)
            self._require_workspace_access(
                session,
                user_id=user_id,
                workspace_id=project.workspace_id,
                write=True,
            )
            dataset.target_column = target_column
            dataset.updated_at = utc_now()
            project.updated_at = dataset.updated_at

    def latest_dataset_version(
        self,
        *,
        user_id: str,
        dataset_id: str,
        stage: str,
    ) -> DatasetVersionSummary | None:
        with self._sessions() as session:
            dataset = session.get(DatasetRecord, dataset_id)
            if dataset is None:
                raise LookupError("Dataset not found.")
            project = session.get(ProjectRecord, dataset.project_id)
            self._require_workspace_access(
                session,
                user_id=user_id,
                workspace_id=project.workspace_id,
            )
            record = session.scalar(
                select(DatasetVersionRecord)
                .where(
                    DatasetVersionRecord.dataset_id == dataset_id,
                    DatasetVersionRecord.stage == stage,
                )
                .order_by(DatasetVersionRecord.version_number.desc())
                .limit(1)
            )
            return self._version_summary(record) if record is not None else None

    @staticmethod
    def _version_summary(record: DatasetVersionRecord) -> DatasetVersionSummary:
        return DatasetVersionSummary(
            id=record.id,
            dataset_id=record.dataset_id,
            stage=record.stage,
            version_number=record.version_number,
            storage_key=record.storage_key,
            file_format=record.file_format,
            checksum=record.checksum,
            row_count=record.row_count,
            column_count=record.column_count,
            created_at=record.created_at,
        )

    def create_dataset_version(
        self,
        *,
        user_id: str,
        dataset_id: str,
        stage: str,
        storage_key: str,
        file_format: str,
        checksum: str,
        row_count: int,
        column_count: int,
        parent_version_id: str | None = None,
    ) -> DatasetVersionSummary:
        now = utc_now()
        with self._sessions.begin() as session:
            dataset = session.get(DatasetRecord, dataset_id)
            if dataset is None:
                raise LookupError("Dataset not found.")
            project = session.get(ProjectRecord, dataset.project_id)
            self._require_workspace_access(
                session,
                user_id=user_id,
                workspace_id=project.workspace_id,
                write=True,
            )
            previous = session.scalar(
                select(DatasetVersionRecord)
                .where(
                    DatasetVersionRecord.dataset_id == dataset_id,
                    DatasetVersionRecord.stage == stage,
                )
                .order_by(DatasetVersionRecord.version_number.desc())
                .limit(1)
            )
            version_number = 1 if previous is None else previous.version_number + 1
            record = DatasetVersionRecord(
                id=str(uuid4()),
                dataset_id=dataset_id,
                parent_version_id=parent_version_id or (previous.id if previous else None),
                stage=stage,
                version_number=version_number,
                storage_key=storage_key,
                file_format=file_format,
                checksum=checksum,
                row_count=row_count,
                column_count=column_count,
                created_by=user_id,
                created_at=now,
            )
            session.add(record)
            dataset.updated_at = now
            project.active_dataset_id = dataset_id
            project.updated_at = now
            session.flush()
            return self._version_summary(record)

    def project_snapshot_metadata(
        self,
        *,
        user_id: str,
        project_id: str,
        dataset_id: str | None = None,
    ) -> DatasetSnapshotMetadata | ProjectSummary:
        with self._sessions() as session:
            project = session.get(ProjectRecord, project_id)
            if project is None:
                raise LookupError("Project not found.")
            self._require_workspace_access(
                session,
                user_id=user_id,
                workspace_id=project.workspace_id,
            )
            project_summary = self._project_summary(session, project)
            selected_dataset_id = dataset_id or project.active_dataset_id
            if not selected_dataset_id:
                return project_summary
            dataset = session.get(DatasetRecord, selected_dataset_id)
            if dataset is None or dataset.project_id != project.id:
                return project_summary
            records = session.scalars(
                select(DatasetVersionRecord)
                .where(DatasetVersionRecord.dataset_id == dataset.id)
                .order_by(
                    DatasetVersionRecord.stage,
                    DatasetVersionRecord.version_number.desc(),
                )
            ).all()
            latest: dict[str, DatasetVersionSummary] = {}
            for record in records:
                latest.setdefault(record.stage, self._version_summary(record))
            return DatasetSnapshotMetadata(
                project=project_summary,
                dataset_id=dataset.id,
                dataset_name=dataset.name,
                original_filename=dataset.original_filename,
                target_column=dataset.target_column,
                versions=latest,
            )


@lru_cache(maxsize=8)
def repository_for_url(url: str) -> StudioRepository:
    return StudioRepository(url)


def bootstrap_identity(
    identity: UserIdentity,
    *,
    url: str | None = None,
) -> IdentityContext:
    """Register the identity and return its accessible workspaces."""

    repository = repository_for_url(url or database_url())
    return repository.synchronize_identity(identity)
