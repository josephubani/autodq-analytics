"""AutoDQ Studio — a Streamlit interface for the AutoDQ analytics engine."""

from __future__ import annotations

import json
import logging
import sys
import tempfile
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

APP_DIR = Path(__file__).resolve().parent
REPOSITORY_ROOT = APP_DIR.parent

if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from app.autodq_web.presenters import (  # noqa: E402
    action_frame,
    column_catalog,
    dataset_metrics,
    frame_to_csv_bytes,
    frame_to_excel_bytes,
    humanize_identifier,
    issue_frame,
    recommendation_frame,
    to_serializable,
    validation_frame,
)
from app.autodq_web.auth import UserIdentity, require_identity  # noqa: E402
from app.autodq_web.persistence import (  # noqa: E402
    IdentityContext,
    bootstrap_identity,
)
from app.autodq_web.project_store import (  # noqa: E402
    RestoredProject,
    project_service,
)
from app.autodq_web.styles import APP_CSS  # noqa: E402
from autodq import AutoDQ  # noqa: E402
from autodq.visualization.renderers.matplotlib_renderer import (  # noqa: E402
    MatplotlibVisualizationRenderer,
)


NAVIGATION = (
    "Overview",
    "Quality scan",
    "Cleaning lab",
    "Explore",
    "ADQL studio",
)

LOGGER = logging.getLogger(__name__)

ADQL_TEMPLATES = {
    "Quick quality check": """PROFILE;
DIAGNOSE;
MISSING SUMMARY;
DUPLICATES SUMMARY;""",
    "Preview current data": """SELECT *
FROM CURRENT
LIMIT 25;""",
    "Numeric summary": """STATISTICS;
INTERPRET;""",
    "Readiness check": """CORRELATION MIN ABS 0.30;
READINESS;""",
}


def configure_page() -> None:
    st.set_page_config(
        page_title="AutoDQ Studio",
        page_icon="◆",
        layout="wide",
        initial_sidebar_state="expanded",
        menu_items={
            "Get Help": "https://github.com/josephubani/autodq-analytics",
            "Report a bug": "https://github.com/josephubani/autodq-analytics/issues",
            "About": "AutoDQ Studio — data quality and analytics without the boilerplate.",
        },
    )
    st.markdown(APP_CSS, unsafe_allow_html=True)


def initialize_state() -> None:
    defaults = {
        "project": None,
        "dataset_name": None,
        "dataset_fingerprint": None,
        "upload_token": 0,
        "page": "Overview",
        "adql_source": ADQL_TEMPLATES["Quick quality check"],
        "adql_result": None,
        "identity_context": None,
        "active_workspace_id": None,
        "active_workspace_role": None,
        "active_project_id": None,
        "active_dataset_id": None,
        "loaded_project_id": None,
        "loaded_dataset_id": None,
        "persisted_stage_checksums": {},
        "pending_project_selector": None,
        "pending_dataset_selector": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def project() -> AutoDQ | None:
    return st.session_state.project


def workspace_can_edit() -> bool:
    return st.session_state.get("active_workspace_role") in {"owner", "editor"}


def source_frame() -> pd.DataFrame | None:
    current = project()
    return current.state.data if current is not None else None


def stage_frame(stage: str) -> pd.DataFrame | None:
    current = project()
    if current is None:
        return None
    if stage == "cleaned":
        return current.state.cleaned_data
    if stage == "engineered":
        return current.state.engineered_data
    return current.state.data


def safe_uploaded_name(name: str) -> str:
    path = Path(name).name
    stem = "".join(char for char in Path(path).stem if char.isalnum() or char in "-_ ").strip()
    return f"{stem or 'dataset'}{Path(path).suffix.lower()}"


def load_autodq_path(path: Path, *, display_name: str, fingerprint: str) -> AutoDQ:
    with st.spinner("Loading the dataset into AutoDQ…"):
        current = AutoDQ(str(path))
        current.load()
    st.session_state.project = current
    st.session_state.dataset_name = display_name
    st.session_state.dataset_fingerprint = fingerprint
    st.session_state.adql_result = None
    return current


def hydrate_saved_project(restored: RestoredProject) -> None:
    """Restore the active dataset and its latest durable stages into AutoDQ."""

    st.session_state.active_project_id = restored.project.id
    st.session_state.loaded_project_id = restored.project.id
    st.session_state.active_dataset_id = restored.dataset_id
    st.session_state.loaded_dataset_id = restored.dataset_id
    st.session_state.persisted_stage_checksums = restored.stage_checksums or {}
    st.session_state.adql_result = None

    if restored.raw_path is None:
        st.session_state.project = None
        st.session_state.dataset_name = None
        st.session_state.dataset_fingerprint = None
        return

    raw_checksum = (restored.stage_checksums or {}).get("raw", restored.dataset_id or "")
    current = load_autodq_path(
        restored.raw_path,
        display_name=restored.dataset_name or restored.original_filename or "Dataset",
        fingerprint=f"saved:{restored.dataset_id}:{raw_checksum}",
    )
    if restored.current_data is not None:
        current.state.data = restored.current_data.copy()
    if restored.target_column and restored.target_column in current.state.data.columns:
        current.set_target(restored.target_column)
    if restored.cleaned_data is not None:
        current.state.cleaned_data = restored.cleaned_data.copy()
    if restored.engineered_data is not None:
        current.state.engineered_data = restored.engineered_data.copy()


def open_saved_project(project_id: str, dataset_id: str | None = None) -> None:
    context = st.session_state.identity_context
    with st.spinner("Opening the saved project…"):
        restored = project_service().restore_project(
            user_id=context.user_id,
            project_id=project_id,
            dataset_id=dataset_id,
        )
        hydrate_saved_project(restored)


def queue_sidebar_selection(
    project_id: str | None,
    dataset_id: str | None = None,
) -> None:
    st.session_state.pending_project_selector = project_id or ""
    st.session_state.pending_dataset_selector = dataset_id or ""


def save_active_stages(*stages: str) -> None:
    current = project()
    context = st.session_state.identity_context
    project_id = st.session_state.active_project_id
    dataset_id = st.session_state.active_dataset_id
    workspace_id = st.session_state.active_workspace_id
    if (
        current is None
        or not workspace_can_edit()
        or not all((context, project_id, dataset_id, workspace_id))
    ):
        return

    frames = {
        "current": current.state.data,
        "cleaned": current.state.cleaned_data,
        "engineered": current.state.engineered_data,
    }
    checksums = dict(st.session_state.persisted_stage_checksums)
    for stage in stages:
        frame = frames.get(stage)
        if frame is None:
            continue
        version = project_service().save_stage(
            user_id=context.user_id,
            workspace_id=workspace_id,
            project_id=project_id,
            dataset_id=dataset_id,
            stage=stage,
            frame=frame,
            target_column=current.target,
        )
        checksums[stage] = version.checksum
    st.session_state.persisted_stage_checksums = checksums


def save_dataset_payload(
    payload: bytes,
    *,
    filename: str,
    project_name: str | None = None,
) -> None:
    if not workspace_can_edit():
        raise PermissionError("This workspace is read-only for your role.")
    context = st.session_state.identity_context
    workspace_id = st.session_state.active_workspace_id
    safe_name = safe_uploaded_name(filename)
    dataset_name = Path(safe_name).stem
    with tempfile.TemporaryDirectory(prefix="autodq-studio-import-") as directory:
        path = Path(directory) / safe_name
        path.write_bytes(payload)
        candidate = AutoDQ(str(path))
        with st.spinner("Validating and saving the dataset…"):
            frame = candidate.load()
            saved = project_service().save_upload(
                user_id=context.user_id,
                workspace_id=workspace_id,
                project_id=st.session_state.active_project_id,
                project_name=project_name or f"{dataset_name} analysis",
                dataset_name=dataset_name,
                original_filename=safe_name,
                payload=payload,
                frame=frame,
                target_column=None,
            )
            restored = project_service().restore_project(
                user_id=context.user_id,
                project_id=saved.project.id,
                dataset_id=saved.dataset_id,
            )
            hydrate_saved_project(restored)
    st.session_state.upload_token += 1
    queue_sidebar_selection(saved.project.id, saved.dataset_id)


def load_upload(uploaded_file) -> None:
    payload = uploaded_file.getvalue()
    save_dataset_payload(payload, filename=uploaded_file.name)
    st.toast("Dataset saved to the project", icon="✅")
    st.rerun()


def load_sample() -> None:
    path = REPOSITORY_ROOT / "datasets" / "sample" / "sales.csv"
    save_dataset_payload(
        path.read_bytes(),
        filename="sales.csv",
        project_name="Sample sales analysis",
    )
    st.toast("Sample sales dataset saved", icon="✨")
    st.rerun()


def reset_session() -> None:
    clear_active_project()
    queue_sidebar_selection(None)
    st.rerun()


def clear_active_project() -> None:
    """Close the active project without removing identity or workspace state."""

    for key, value in {
        "project": None,
        "dataset_name": None,
        "dataset_fingerprint": None,
        "adql_result": None,
        "active_project_id": None,
        "active_dataset_id": None,
        "loaded_project_id": None,
        "loaded_dataset_id": None,
        "persisted_stage_checksums": {},
    }.items():
        st.session_state[key] = value
    st.session_state.pop("visualization_result", None)


def clear_session_state() -> None:
    """Remove all session state before signing out."""

    for key in list(st.session_state):
        del st.session_state[key]


def logout_session() -> None:
    clear_session_state()
    st.logout()


def load_identity_context(identity: UserIdentity) -> IdentityContext | None:
    cached = st.session_state.get("identity_context")
    if cached is not None and cached.identity_key == identity.identity_key:
        return cached

    try:
        with st.spinner("Preparing your AutoDQ workspace…"):
            context = bootstrap_identity(identity)
    except Exception:
        LOGGER.exception("AutoDQ Studio workspace initialization failed")
        st.error(
            "AutoDQ could not prepare your workspace. Check the database "
            "configuration and try again."
        )
        return None

    st.session_state.identity_context = context
    workspace_ids = {workspace.id for workspace in context.workspaces}
    if st.session_state.get("active_workspace_id") not in workspace_ids:
        st.session_state.active_workspace_id = context.personal_workspace.id
    return context


def render_brand() -> None:
    st.markdown(
        """
        <div class="dq-brand">
          <div class="dq-mark">DQ</div>
          <div><strong>AutoDQ Studio</strong><span>Quality intelligence workspace</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def apply_pending_selector(selector_key: str, pending_key: str, default: str) -> None:
    pending = st.session_state.get(pending_key)
    if pending is not None:
        st.session_state[selector_key] = pending
        st.session_state[pending_key] = None
    elif selector_key not in st.session_state:
        st.session_state[selector_key] = default


def refresh_identity_context(
    identity: UserIdentity,
    *,
    preferred_workspace_id: str | None = None,
) -> IdentityContext:
    context = bootstrap_identity(identity)
    st.session_state.identity_context = context
    workspace_ids = {workspace.id for workspace in context.workspaces}
    preferred = preferred_workspace_id or st.session_state.active_workspace_id
    st.session_state.active_workspace_id = (
        preferred if preferred in workspace_ids else context.personal_workspace.id
    )
    return context


def render_workspace_manager(
    identity: UserIdentity,
    context: IdentityContext,
    workspace,
) -> None:
    repository = project_service().repository
    with st.expander("Workspace & members"):
        if st.button("Refresh workspace access", width="stretch"):
            refresh_identity_context(identity)
            st.toast("Workspace access refreshed", icon="✅")
            st.rerun()

        st.markdown("**Create a team workspace**")
        with st.form(
            "create_team_workspace_form",
            clear_on_submit=True,
            enter_to_submit=False,
        ):
            team_name = st.text_input(
                "Team workspace name",
                placeholder="Revenue operations",
            )
            create_team = st.form_submit_button(
                "Create team workspace",
                width="stretch",
            )
        if create_team:
            try:
                created = repository.create_team_workspace(
                    user_id=context.user_id,
                    name=team_name,
                )
            except (ValueError, LookupError) as error:
                st.error(str(error))
            else:
                clear_active_project()
                refresh_identity_context(
                    identity,
                    preferred_workspace_id=created.id,
                )
                st.toast("Team workspace created", icon="✅")
                st.rerun()

        if workspace.is_personal:
            st.caption("Personal workspaces are private to their owner.")
            return

        members = repository.list_workspace_members(
            user_id=context.user_id,
            workspace_id=workspace.id,
        )
        st.markdown(f"**Members · {len(members)}**")
        for member in members:
            owner_label = " · owner" if member.is_owner else ""
            address = f" · {member.email}" if member.email else ""
            st.caption(
                f"{member.display_name}{address} · {member.role}{owner_label}"
            )

        if workspace.role != "owner":
            st.caption("Only the workspace owner can manage members.")
            return

        st.markdown("**Invite a member**")
        with st.form(
            "invite_workspace_member_form",
            clear_on_submit=True,
            enter_to_submit=False,
        ):
            invite_email = st.text_input(
                "Verified email",
                placeholder="analyst@example.com",
            )
            invite_role = st.selectbox(
                "Role",
                ("editor", "reviewer", "viewer"),
                format_func=str.title,
            )
            invite_submitted = st.form_submit_button(
                "Send invitation",
                type="primary",
                width="stretch",
            )
        if invite_submitted:
            try:
                repository.invite_workspace_member(
                    user_id=context.user_id,
                    workspace_id=workspace.id,
                    email=invite_email,
                    role=invite_role,
                )
            except (ValueError, LookupError, PermissionError) as error:
                st.error(str(error))
            else:
                st.toast("Invitation saved", icon="✅")
                st.rerun()
        st.caption(
            "The invitation activates when that verified email next signs in."
        )

        manageable = [member for member in members if not member.is_owner]
        if manageable:
            labels = {
                f"{member.display_name} · {member.email or member.user_id}": member
                for member in manageable
            }
            st.markdown("**Manage a member**")
            with st.form(
                "manage_workspace_member_form",
                enter_to_submit=False,
            ):
                member_label = st.selectbox("Member", tuple(labels))
                selected_member = labels[member_label]
                roles = ("editor", "reviewer", "viewer")
                member_role = st.selectbox(
                    "Member role",
                    roles,
                    index=roles.index(selected_member.role),
                    format_func=str.title,
                )
                update_column, remove_column = st.columns(2)
                with update_column:
                    update_member = st.form_submit_button(
                        "Update role",
                        width="stretch",
                    )
                with remove_column:
                    remove_member = st.form_submit_button(
                        "Remove",
                        width="stretch",
                    )
            if update_member:
                repository.update_workspace_member_role(
                    user_id=context.user_id,
                    workspace_id=workspace.id,
                    member_user_id=selected_member.user_id,
                    role=member_role,
                )
                st.toast("Member role updated", icon="✅")
                st.rerun()
            if remove_member:
                repository.remove_workspace_member(
                    user_id=context.user_id,
                    workspace_id=workspace.id,
                    member_user_id=selected_member.user_id,
                )
                st.toast("Member removed", icon="✅")
                st.rerun()

        invitations = repository.list_workspace_invitations(
            user_id=context.user_id,
            workspace_id=workspace.id,
        )
        if invitations:
            st.markdown(f"**Pending invitations · {len(invitations)}**")
            for invitation in invitations:
                label, action = st.columns([3, 1])
                with label:
                    st.caption(f"{invitation.email} · {invitation.role}")
                with action:
                    if st.button(
                        "Revoke",
                        key=f"revoke_invitation_{invitation.id}",
                    ):
                        repository.revoke_workspace_invitation(
                            user_id=context.user_id,
                            workspace_id=workspace.id,
                            invitation_id=invitation.id,
                        )
                        st.toast("Invitation revoked", icon="✅")
                        st.rerun()


def render_project_picker(
    context: IdentityContext,
    *,
    can_write: bool,
) -> None:
    service = project_service()
    workspace_id = st.session_state.active_workspace_id
    projects = service.list_projects(
        user_id=context.user_id,
        workspace_id=workspace_id,
    )
    project_map = {item.id: item for item in projects}
    project_name_map = {item.name: item.id for item in projects}
    project_options = [""] + list(project_name_map)
    current_project_id = st.session_state.active_project_id
    if current_project_id not in project_map:
        current_project_id = None
        clear_active_project()

    pending_project_id = st.session_state.get("pending_project_selector")
    if pending_project_id is not None:
        st.session_state.pending_project_selector = (
            project_map[pending_project_id].name
            if pending_project_id in project_map
            else ""
        )
    default_project_name = (
        project_map[current_project_id].name if current_project_id in project_map else ""
    )
    apply_pending_selector(
        "project_selector",
        "pending_project_selector",
        default_project_name,
    )
    if st.session_state.project_selector not in project_options:
        st.session_state.project_selector = ""
    selected_project_name = st.selectbox(
        "Project",
        project_options,
        key="project_selector",
        format_func=lambda value: value or "Choose a saved project",
    )
    selected_project_id = project_name_map.get(selected_project_name, "")
    if selected_project_id != (st.session_state.active_project_id or ""):
        if selected_project_id:
            open_saved_project(selected_project_id)
        else:
            clear_active_project()
        st.rerun()

    with st.expander("Create a project"):
        if not can_write:
            st.caption("Your workspace role has read-only project access.")
        else:
            with st.form(
                "create_project_form",
                clear_on_submit=True,
                enter_to_submit=False,
            ):
                name = st.text_input(
                    "Project name",
                    placeholder="Quarterly sales review",
                )
                description = st.text_area(
                    "Description",
                    placeholder="Optional context for this analysis",
                    height=70,
                )
                submitted = st.form_submit_button(
                    "Create project",
                    type="primary",
                    width="stretch",
                )
            if submitted:
                created = service.create_project(
                    user_id=context.user_id,
                    workspace_id=workspace_id,
                    name=name,
                    description=description,
                )
                open_saved_project(created.id)
                queue_sidebar_selection(created.id)
                st.toast("Project created", icon="✅")
                st.rerun()

    active_project_id = st.session_state.active_project_id
    if not active_project_id:
        return

    datasets = service.list_datasets(
        user_id=context.user_id,
        project_id=active_project_id,
    )
    if not datasets:
        st.caption("This project is ready for its first dataset.")
        return

    dataset_map = {item.id: item for item in datasets}
    dataset_name_map = {item.name: item.id for item in datasets}
    default_dataset = (
        st.session_state.active_dataset_id
        if st.session_state.active_dataset_id in dataset_map
        else datasets[0].id
    )
    pending_dataset_id = st.session_state.get("pending_dataset_selector")
    if pending_dataset_id is not None:
        st.session_state.pending_dataset_selector = (
            dataset_map[pending_dataset_id].name
            if pending_dataset_id in dataset_map
            else ""
        )
    default_dataset_name = dataset_map[default_dataset].name
    apply_pending_selector(
        "dataset_selector",
        "pending_dataset_selector",
        default_dataset_name,
    )
    if st.session_state.dataset_selector not in dataset_name_map:
        st.session_state.dataset_selector = default_dataset_name
    selected_dataset_name = st.selectbox(
        "Dataset",
        list(dataset_name_map),
        key="dataset_selector",
    )
    selected_dataset_id = dataset_name_map[selected_dataset_name]
    if selected_dataset_id != st.session_state.active_dataset_id:
        open_saved_project(active_project_id, selected_dataset_id)
        st.rerun()


def render_sidebar(identity: UserIdentity, context: IdentityContext) -> str:
    with st.sidebar:
        render_brand()
        st.markdown(f"**{identity.display_name}**")
        if identity.email:
            st.caption(identity.email)
        if identity.is_development:
            st.markdown(
                '<span class="dq-status"><span class="dq-dot"></span>Local development</span>',
                unsafe_allow_html=True,
            )
        elif st.button("Log out", width="stretch"):
            logout_session()

        st.markdown('<div class="dq-divider"></div>', unsafe_allow_html=True)
        workspace_map = {workspace.id: workspace for workspace in context.workspaces}
        workspace_ids = list(workspace_map)
        selected_workspace = st.selectbox(
            "Workspace",
            workspace_ids,
            index=workspace_ids.index(st.session_state.active_workspace_id),
            format_func=lambda workspace_id: workspace_map[workspace_id].name,
            disabled=len(workspace_ids) == 1,
        )
        if selected_workspace != st.session_state.active_workspace_id:
            clear_active_project()
            st.session_state.active_workspace_id = selected_workspace
            st.session_state.pop("project_selector", None)
            st.session_state.pop("dataset_selector", None)
        selected_summary = workspace_map[selected_workspace]
        st.session_state.active_workspace_role = selected_summary.role
        workspace_kind = "Personal workspace" if selected_summary.is_personal else "Team workspace"
        st.caption(f"{selected_summary.role.title()} · {workspace_kind}")

        render_workspace_manager(
            identity,
            context,
            selected_summary,
        )

        st.markdown('<div class="dq-divider"></div>', unsafe_allow_html=True)
        try:
            render_project_picker(
                context,
                can_write=workspace_can_edit(),
            )
        except Exception as error:
            LOGGER.exception("AutoDQ Studio project navigation failed")
            st.error(f"Saved projects could not be loaded: {error}")

        st.markdown('<div class="dq-divider"></div>', unsafe_allow_html=True)
        uploaded = st.file_uploader(
            "Add a dataset" if st.session_state.active_project_id else "Upload a dataset",
            type=("csv", "xlsx", "xls"),
            key=f"dataset_upload_{st.session_state.upload_token}",
            help="The original file is saved privately in the selected workspace.",
            disabled=not workspace_can_edit(),
        )
        if uploaded is not None:
            load_upload(uploaded)

        sample_disabled = (
            not workspace_can_edit()
            or not (REPOSITORY_ROOT / "datasets" / "sample" / "sales.csv").exists()
        )
        if st.button(
            "Use sample sales data",
            width="stretch",
            disabled=sample_disabled,
        ):
            load_sample()

        current = project()
        if current is not None and current.state.data is not None:
            st.markdown('<div class="dq-divider"></div>', unsafe_allow_html=True)
            st.markdown(
                '<span class="dq-status"><span class="dq-dot"></span>Dataset active</span>',
                unsafe_allow_html=True,
            )
            st.caption(st.session_state.dataset_name)

            columns = list(current.state.data.columns)
            options = ["No target"] + columns
            active_target = current.target if current.target in columns else "No target"
            selected = st.selectbox(
                "Prediction target",
                options,
                index=options.index(active_target),
                help="Optional. Needed for readiness, modeling, and SHAP workflows.",
                disabled=not workspace_can_edit(),
            )
            target = None if selected == "No target" else selected
            if target != current.target:
                if target is None:
                    current.state.target = None
                    current._invalidate_target_pipeline()
                else:
                    current.set_target(target)
                project_service().update_target(
                    user_id=context.user_id,
                    dataset_id=st.session_state.active_dataset_id,
                    target_column=target,
                )
                st.toast("Prediction target saved", icon="✅")

            st.markdown('<div class="dq-divider"></div>', unsafe_allow_html=True)
            page = st.radio(
                "Workspace",
                NAVIGATION,
                key="page",
                label_visibility="collapsed",
            )
            st.markdown('<div class="dq-divider"></div>', unsafe_allow_html=True)
            if st.button("Close project", width="stretch"):
                reset_session()
            return page

        st.markdown('<div class="dq-divider"></div>', unsafe_allow_html=True)
        st.caption("Choose a project, upload CSV or Excel, or use the bundled sales example.")
        return "Overview"


def page_title(kicker: str, title: str, description: str) -> None:
    st.markdown(
        f"""
        <div class="dq-page-title">
          <small>{kicker}</small>
          <h1>{title}</h1>
          <p>{description}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def feature_card(eyebrow: str, title: str, description: str) -> None:
    st.markdown(
        f"""
        <div class="dq-card">
          <div class="eyebrow">{eyebrow}</div>
          <h3>{title}</h3>
          <p>{description}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_empty_state() -> None:
    st.markdown(
        """
        <section class="dq-hero">
          <div class="dq-kicker">AutoDQ · Studio v1.1</div>
          <h1>From raw data to trusted decisions.</h1>
          <p>Profile quality, review evidence-backed cleaning actions, explore patterns, and run ADQL in one focused workspace.</p>
        </section>
        """,
        unsafe_allow_html=True,
    )
    left, middle, right = st.columns(3)
    with left:
        feature_card("01 · Inspect", "Know the dataset", "Immediate structure, completeness, duplicate, and semantic-type signals.")
    with middle:
        feature_card("02 · Improve", "Clean with evidence", "Review recommendations before applying traceable changes to your data.")
    with right:
        feature_card("03 · Analyze", "Move beyond cleaning", "Create visuals and execute ADQL against the same in-memory project.")

    st.write("")
    action, note = st.columns([1, 2])
    with action:
        if st.button("Explore with sample data", type="primary", width="stretch"):
            load_sample()
    with note:
        st.markdown(
            '<p class="dq-note">Projects and dataset versions are saved automatically in your private workspace, so you can close the app and continue later.</p>',
            unsafe_allow_html=True,
        )


def metric_row(frame: pd.DataFrame, *, quality_score: float | None = None) -> None:
    metrics = dataset_metrics(frame)
    columns = st.columns(5)
    columns[0].metric("Rows", f"{metrics['rows']:,}")
    columns[1].metric("Columns", f"{metrics['columns']:,}")
    columns[2].metric("Missing cells", f"{metrics['missing']:,}", f"{metrics['missing_percent']:.2f}%")
    columns[3].metric("Duplicate rows", f"{metrics['duplicates']:,}", f"{metrics['duplicate_percent']:.2f}%")
    score = quality_score if quality_score is not None else metrics["completeness"]
    columns[4].metric("Quality score" if quality_score is not None else "Completeness", f"{score:.2f}")


def run_quality_scan() -> None:
    current = project()
    if current is None:
        return
    with st.spinner("AutoDQ is profiling, diagnosing, and building recommendations…"):
        current.profile()
        current.diagnose()
        current.recommend()
        current.decide()
        current.preview()
    st.toast("Quality scan completed", icon="✅")
    st.rerun()


def render_overview() -> None:
    current = project()
    frame = current.state.data
    page_title(
        "Workspace overview",
        st.session_state.dataset_name,
        "A live view of the active dataset and the latest saved analysis stages.",
    )
    quality_score = (
        current.state.diagnosis_report.quality_score
        if current.state.diagnosis_report is not None
        else None
    )
    metric_row(frame, quality_score=quality_score)

    st.write("")
    left, right = st.columns([1.45, 1])
    with left:
        st.subheader("Data preview")
        st.dataframe(frame.head(50), width="stretch", hide_index=True)
    with right:
        st.subheader("Workflow progress")
        stages = [
            ("Profile", current.state.profile_report is not None),
            ("Diagnosis", current.state.diagnosis_report is not None),
            ("Cleaning plan", current.state.decision_plan is not None),
            ("Cleaned data", current.state.cleaned_data is not None),
            ("Validation", current.state.validation_report is not None),
            ("ADQL run", bool(current.adql_history)),
        ]
        for label, complete in stages:
            icon = "✓" if complete else "○"
            color = "#66e5bd" if complete else "#78918b"
            st.markdown(f"<div style='padding:.47rem 0;color:{color};font-weight:650'>{icon}&nbsp;&nbsp;{label}</div>", unsafe_allow_html=True)
        st.write("")
        if st.button("Run quick quality scan", type="primary", width="stretch"):
            run_quality_scan()

    st.subheader("Column catalogue")
    st.dataframe(column_catalog(frame), width="stretch", hide_index=True)


def render_quality() -> None:
    current = project()
    page_title(
        "Quality intelligence",
        "Quality scan",
        "Surface missingness, duplication, outliers, datatype signals, and evidence-backed recommendations.",
    )
    if current.state.diagnosis_report is None:
        st.info("Run the scan to create a profile, diagnosis, statistical evidence, recommendations, and a cleaning plan.")
        if st.button("Run full quality scan", type="primary"):
            run_quality_scan()
        return

    report = current.state.diagnosis_report
    metric_row(current.state.data, quality_score=report.quality_score)
    st.write("")
    summary, action = st.columns([3, 1])
    with summary:
        st.markdown(f"**AutoDQ summary:** {report.summary or 'Quality analysis completed.'}")
    with action:
        if st.button("Refresh scan", width="stretch"):
            run_quality_scan()

    issues = issue_frame(report)
    tab_issues, tab_missing, tab_duplicates, tab_recommend = st.tabs(
        ("Issues", "Missing values", "Duplicate rows", "Recommendations")
    )
    with tab_issues:
        if issues.empty:
            st.success("No data-quality issues were detected.")
        else:
            st.dataframe(issues, width="stretch", hide_index=True)
    with tab_missing:
        missing = current.missing_summary()
        st.dataframe(missing, width="stretch", hide_index=True)
        chart_data = missing.loc[missing["missing"] > 0, ["column", "missing"]]
        if not chart_data.empty:
            st.bar_chart(chart_data.set_index("column"), color="#2dd4a3")
    with tab_duplicates:
        duplicates = current.duplicate_summary()
        if duplicates.empty:
            st.success("No exact duplicate rows were found.")
        else:
            st.caption(f"Showing {min(len(duplicates), 100):,} of {len(duplicates):,} duplicate-row occurrences.")
            st.dataframe(duplicates.head(100), width="stretch", hide_index=True)
    with tab_recommend:
        recommendations = recommendation_frame(current.state.recommendations)
        if recommendations.empty:
            st.success("No cleaning recommendations are required.")
        else:
            st.dataframe(recommendations, width="stretch", hide_index=True)


def prepare_review() -> None:
    current = project()
    if current.state.decision_plan is None:
        current.profile()
        current.diagnose()
        current.recommend()
        current.decide()
        current.preview()
    with st.spinner("Preparing the interactive cleaning review…"):
        current.review_cleaning(auto_display=False)
    st.toast("Cleaning review is ready", icon="🧹")
    st.rerun()


def render_cleaning() -> None:
    current = project()
    editable = workspace_can_edit()
    page_title(
        "Governed cleaning",
        "Cleaning lab",
        "Approve automatic actions, handle missing values and duplicates manually, then validate every change.",
    )
    if not editable:
        st.info(
            "This workspace is read-only for your role. You can inspect and "
            "download results, but only owners and editors can change data."
        )
    if current.state.cleaning_review is None:
        if current.state.cleaned_data is not None:
            st.success("The latest cleaned dataset was restored from this saved project.")
            st.dataframe(
                current.state.cleaned_data.head(100),
                width="stretch",
                hide_index=True,
            )
            download_exports(current.state.cleaned_data, prefix="autodq-cleaned")
            if st.button(
                "Prepare a new cleaning review",
                disabled=not editable,
            ):
                prepare_review()
        else:
            st.info("Prepare a review to inspect every proposed cleaning action before data is changed.")
            if st.button(
                "Prepare cleaning review",
                type="primary",
                disabled=not editable,
            ):
                prepare_review()
        return

    review = current.state.cleaning_review
    counts = st.columns(4)
    counts[0].metric("Actions", review.action_count)
    counts[1].metric("Pending", review.pending_count)
    counts[2].metric("Approved", review.approved_count)
    counts[3].metric("Rejected", review.rejected_count)

    actions = action_frame(review)
    if actions.empty:
        st.success("No automatic cleaning actions are required. Manual tools remain available below.")
    else:
        st.dataframe(actions, width="stretch", hide_index=True)
        options = actions["ID"].tolist()
        selected = st.multiselect(
            "Select action IDs",
            options,
            format_func=lambda value: f"#{value} · {actions.loc[actions['ID'] == value, 'Issue'].iloc[0]}",
        )
        approve, reject, apply_all = st.columns([1, 1, 1.35])
        with approve:
            if st.button(
                "Approve selected",
                disabled=not selected or not editable,
                width="stretch",
            ):
                current.approve(selected)
                st.rerun()
        with reject:
            if st.button(
                "Reject selected",
                disabled=not selected or not editable,
                width="stretch",
            ):
                current.reject(selected, reason="Rejected in AutoDQ Studio")
                st.rerun()
        with apply_all:
            if st.button(
                "Approve all and clean",
                type="primary",
                width="stretch",
                disabled=not editable,
            ):
                with st.spinner("Applying approved actions and validating the result…"):
                    current.approve_all()
                    current.clean()
                    current.validate_cleaning()
                    save_active_stages("cleaned")
                st.toast("Cleaned dataset created", icon="✅")
                st.rerun()

    tab_missing, tab_duplicates, tab_outliers, tab_result = st.tabs(
        ("Missing values", "Duplicates", "Outliers", "Cleaned result")
    )
    with tab_missing:
        summary = current.missing_summary()
        st.dataframe(summary, width="stretch", hide_index=True)
        affected = summary.loc[summary["missing"] > 0, "column"].tolist()
        if affected:
            selected_columns = st.multiselect(
                "Columns to fill",
                summary["column"].tolist(),
                default=affected,
                key="missing_columns",
            )
            strategy = st.selectbox(
                "Strategy",
                ("auto", "median", "mean", "mode", "zero", "ffill", "bfill", "interpolate", "constant"),
            )
            constant = st.text_input("Constant value", disabled=strategy != "constant")
            if st.button(
                "Stage missing-value treatment",
                disabled=not selected_columns or not editable,
            ):
                value = constant if strategy == "constant" else None
                current.fill_missing(selected_columns, strategy=strategy, value=value, reason="Staged in AutoDQ Studio")
                st.toast("Missing-value treatment staged", icon="✅")
                st.rerun()
        else:
            st.success("No missing values remain in the review data.")
    with tab_duplicates:
        duplicates = current.duplicate_summary()
        if duplicates.empty:
            st.success("No exact duplicate rows remain.")
        else:
            st.dataframe(duplicates.head(100), width="stretch", hide_index=True)
            if st.button(
                "Stage duplicate removal",
                key="drop_duplicates",
                disabled=not editable,
            ):
                current.drop_duplicates(keep="first", reason="Staged in AutoDQ Studio")
                st.toast("Duplicate removal staged", icon="✅")
                st.rerun()
    with tab_outliers:
        if st.button("Review numeric outliers"):
            current.review_outliers()
            st.rerun()
        outlier_report = review.outlier_report
        if outlier_report is not None:
            st.metric("Outlier observations", outlier_report.outlier_count)
            records = pd.DataFrame([item.to_dict() for item in outlier_report.records])
            if records.empty:
                st.success("No IQR outliers were detected.")
            else:
                st.dataframe(records.head(200), width="stretch", hide_index=True)
    with tab_result:
        cleaned = current.state.cleaned_data
        if cleaned is None:
            st.caption("Apply the reviewed cleaning plan to create a validated cleaned dataset.")
        else:
            validation = current.state.validation_report
            if validation is not None:
                before, after, delta = st.columns(3)
                before.metric("Quality before", f"{validation.quality_score_before:.2f}")
                after.metric("Quality after", f"{validation.quality_score_after:.2f}")
                delta.metric("Quality change", f"{validation.quality_score_change:+.2f}")
                st.dataframe(validation_frame(validation), width="stretch", hide_index=True)
            st.dataframe(cleaned.head(100), width="stretch", hide_index=True)
            download_exports(cleaned, prefix="autodq-cleaned")


def available_stages() -> dict[str, str]:
    current = project()
    stages = {"Current data": "current"}
    if current.state.cleaned_data is not None:
        stages["Cleaned data"] = "cleaned"
    if current.state.engineered_data is not None:
        stages["Engineered data"] = "engineered"
    return stages


def render_chart_report(report) -> None:
    if report is None or not report.charts:
        st.warning("No visualization was generated for this selection.")
        return
    renderer = MatplotlibVisualizationRenderer()
    for chart in report.charts:
        st.markdown(f"#### {chart.title}")
        st.caption(chart.description)
        figure, _ = renderer.build_figure(chart)
        st.pyplot(figure, width="stretch")
        plt.close(figure)


def render_explore() -> None:
    current = project()
    page_title(
        "Visual analytics",
        "Explore",
        "Build reusable AutoDQ charts against the current, cleaned, or engineered stage.",
    )
    stage_options = available_stages()
    stage_label = st.selectbox("Dataset stage", tuple(stage_options))
    stage = stage_options[stage_label]
    frame = stage_frame(stage)
    numeric = list(frame.select_dtypes(include="number").columns)
    all_columns = list(frame.columns)
    chart_types = ["auto", "missing_values", "distribution"]
    if numeric:
        chart_types.extend(("histogram", "boxplot", "bar"))
    if len(numeric) >= 2:
        chart_types.extend(("scatter", "correlation_heatmap"))

    controls = st.columns([1, 1, 1])
    with controls[0]:
        chart = st.selectbox(
            "Chart type",
            chart_types,
            format_func=lambda value: humanize_identifier(value).title(),
        )
    x = y = column = None
    with controls[1]:
        if chart in {"distribution", "histogram", "boxplot"}:
            candidates = numeric if chart in {"histogram", "boxplot"} else all_columns
            column = st.selectbox("Column", candidates or all_columns)
        elif chart in {"bar", "scatter"}:
            x_candidates = numeric if chart == "scatter" else all_columns
            x = st.selectbox("X axis", x_candidates)
    with controls[2]:
        if chart in {"bar", "scatter"}:
            y = st.selectbox("Y axis", numeric)

    title = st.text_input("Optional chart title")
    if st.button("Generate visualization", type="primary"):
        try:
            with st.spinner("Rendering with AutoDQ…"):
                report = current.visualize(
                    chart=chart,
                    x=x,
                    y=y,
                    column=column,
                    stage=stage,
                    append=False,
                    display=False,
                    title=title or None,
                    theme="dark",
                    grid=True,
                )
            st.session_state.visualization_result = report
        except Exception as error:
            st.error(f"Visualization failed: {error}")

    report = st.session_state.get("visualization_result")
    if report is not None:
        render_chart_report(report)

    with st.expander("Preview selected stage"):
        st.dataframe(frame.head(100), width="stretch", hide_index=True)


def render_adql_result(run) -> None:
    summary = st.columns(4)
    summary[0].metric("Statements", run.statement_count)
    summary[1].metric("Completed", run.completed_count)
    summary[2].metric("Failed", run.failed_count)
    summary[3].metric("Runtime", f"{run.duration_seconds:.3f}s")

    for index, result in enumerate(run.results, start=1):
        icon = "✅" if result.success else "❌"
        with st.expander(f"{icon} Statement {index} · {result.statement.kind}", expanded=True):
            st.code(result.statement.raw, language="sql")
            if result.success:
                st.success(result.message)
            else:
                st.error(result.error_message or result.message)
            if result.data is not None and result.display_data:
                st.dataframe(result.data, width="stretch", hide_index=True)
            elif result.value is not None:
                st.json(to_serializable(result.value), expanded=False)


def render_adql() -> None:
    current = project()
    editable = workspace_can_edit()
    page_title(
        "Native analytics language",
        "ADQL studio",
        "Run ADQL directly against the same in-memory project. Commands can inspect, clean, analyze, and register reusable datasets.",
    )
    if not editable:
        st.info(
            "ADQL execution is disabled for read-only workspace roles because "
            "a notebook can contain data-changing commands."
        )
    template, action = st.columns([2, 1])
    with template:
        selected_template = st.selectbox("Starter", tuple(ADQL_TEMPLATES))
    with action:
        st.write("")
        if st.button("Load starter", width="stretch"):
            st.session_state.adql_source = ADQL_TEMPLATES[selected_template]
            st.rerun()

    source = st.text_area(
        "ADQL",
        key="adql_source",
        height=260,
        help="Statements end with semicolons. Commands are case-insensitive.",
    )
    run_column, clear_column, help_column = st.columns([1, 1, 2])
    with run_column:
        run_clicked = st.button(
            "Run ADQL",
            type="primary",
            width="stretch",
            disabled=not editable,
        )
    with clear_column:
        if st.button("Clear output", width="stretch"):
            st.session_state.adql_result = None
            st.rerun()
    with help_column:
        st.caption("Tip: use double quotes for readable identifiers and single quotes for text or paths.")

    if run_clicked:
        try:
            with st.spinner("Executing ADQL…"):
                st.session_state.adql_result = current.query(
                    source,
                    auto_display=False,
                    source_name="streamlit",
                    base_path=REPOSITORY_ROOT,
                )
                save_active_stages("current", "cleaned", "engineered")
            st.toast("ADQL completed", icon="✅")
        except Exception as error:
            st.session_state.adql_result = None
            st.error(f"ADQL execution failed: {error}")

    if st.session_state.adql_result is not None:
        render_adql_result(st.session_state.adql_result)


def download_exports(frame: pd.DataFrame, *, prefix: str) -> None:
    csv_column, excel_column = st.columns(2)
    with csv_column:
        st.download_button(
            "Download CSV",
            frame_to_csv_bytes(frame),
            file_name=f"{prefix}.csv",
            mime="text/csv",
            width="stretch",
        )
    with excel_column:
        st.download_button(
            "Download Excel",
            frame_to_excel_bytes(frame),
            file_name=f"{prefix}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            width="stretch",
        )


def main() -> None:
    configure_page()
    identity = require_identity()
    if identity is None:
        return
    initialize_state()
    identity_context = load_identity_context(identity)
    if identity_context is None:
        return
    st.session_state.auth_identity = identity
    page = render_sidebar(identity, identity_context)
    if project() is None:
        render_empty_state()
        return

    renderers = {
        "Overview": render_overview,
        "Quality scan": render_quality,
        "Cleaning lab": render_cleaning,
        "Explore": render_explore,
        "ADQL studio": render_adql,
    }
    renderers[page]()


if __name__ == "__main__":
    main()
