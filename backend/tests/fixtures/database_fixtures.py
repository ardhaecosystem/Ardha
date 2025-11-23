"""
Database test fixtures for integration and unit tests.

This module provides pytest fixtures for database system testing using
direct database model creation for reliable test setup.
"""

from typing import List
from uuid import UUID, uuid4

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from ardha.models.database import Database
from ardha.models.database_entry import DatabaseEntry
from ardha.models.database_entry_value import DatabaseEntryValue
from ardha.models.database_property import DatabaseProperty
from ardha.models.database_view import DatabaseView
from ardha.models.project import Project
from ardha.models.project_member import ProjectMember
from ardha.models.user import User
from ardha.services.auth_service import pwd_context


@pytest_asyncio.fixture
async def sample_database(
    test_db: AsyncSession,
    test_project: dict,
    test_user: dict,
) -> Database:
    """Create sample Database using database model with test_user's project."""
    database = Database(
        project_id=UUID(test_project["id"]),
        name="Task Tracker",
        description="Track project tasks",
        icon="✅",
        color="#10B981",
        created_by_user_id=UUID(test_user["user"]["id"]),
    )
    test_db.add(database)
    await test_db.flush()
    await test_db.refresh(database)
    return database


@pytest_asyncio.fixture
async def sample_properties(
    test_db: AsyncSession,
    sample_database: Database,
) -> List[DatabaseProperty]:
    """Create 5 sample properties."""
    properties = [
        DatabaseProperty(
            database_id=sample_database.id,
            name="Title",
            property_type="text",
            config={},
            position=0,
            is_required=True,
            is_visible=True,
        ),
        DatabaseProperty(
            database_id=sample_database.id,
            name="Status",
            property_type="select",
            config={
                "options": [
                    {"name": "To Do", "color": "#6B7280"},
                    {"name": "In Progress", "color": "#3B82F6"},
                    {"name": "Done", "color": "#10B981"},
                ]
            },
            position=1,
            is_required=False,
            is_visible=True,
        ),
        DatabaseProperty(
            database_id=sample_database.id,
            name="Priority",
            property_type="select",
            config={
                "options": [
                    {"name": "Low", "color": "#6B7280"},
                    {"name": "Medium", "color": "#F59E0B"},
                    {"name": "High", "color": "#EF4444"},
                ]
            },
            position=2,
            is_required=False,
            is_visible=True,
        ),
        DatabaseProperty(
            database_id=sample_database.id,
            name="Due Date",
            property_type="date",
            config={},
            position=3,
            is_required=False,
            is_visible=True,
        ),
        DatabaseProperty(
            database_id=sample_database.id,
            name="Effort",
            property_type="number",
            config={"format": "number"},
            position=4,
            is_required=False,
            is_visible=True,
        ),
    ]

    for prop in properties:
        test_db.add(prop)

    await test_db.flush()
    for prop in properties:
        await test_db.refresh(prop)

    return properties


@pytest_asyncio.fixture
async def sample_views(
    test_db: AsyncSession,
    test_user: dict,
    sample_database: Database,
) -> List[DatabaseView]:
    """Create 3 sample views using test_user."""
    user_id = UUID(test_user["user"]["id"])

    views = [
        DatabaseView(
            database_id=sample_database.id,
            name="All",
            view_type="table",
            config={"filters": [], "sorts": []},
            position=0,
            is_default=True,
            created_by_user_id=user_id,
        ),
        DatabaseView(
            database_id=sample_database.id,
            name="Board",
            view_type="board",
            config={"group_by_property": "status", "filters": []},
            position=1,
            is_default=False,
            created_by_user_id=user_id,
        ),
        DatabaseView(
            database_id=sample_database.id,
            name="List",
            view_type="list",
            config={"filters": []},
            position=2,
            is_default=False,
            created_by_user_id=user_id,
        ),
    ]

    for view in views:
        test_db.add(view)

    await test_db.flush()
    for view in views:
        await test_db.refresh(view)

    return views


@pytest_asyncio.fixture
async def sample_entries(
    test_db: AsyncSession,
    test_user: dict,
    sample_database: Database,
) -> List[DatabaseEntry]:
    """Create 10 sample entries using test_user."""
    user_id = UUID(test_user["user"]["id"])

    entries = []
    for i in range(10):
        entry = DatabaseEntry(
            database_id=sample_database.id,
            position=i,
            created_by_user_id=user_id,
            last_edited_by_user_id=user_id,
        )
        test_db.add(entry)
        entries.append(entry)

    await test_db.flush()
    for entry in entries:
        await test_db.refresh(entry)

    return entries


@pytest_asyncio.fixture
async def sample_entry_values(
    test_db: AsyncSession,
    sample_entries: List[DatabaseEntry],
    sample_properties: List[DatabaseProperty],
) -> List[DatabaseEntryValue]:
    """Create entry values for all entries."""
    values = []
    prop_map = {p.name: p for p in sample_properties}

    for i, entry in enumerate(sample_entries):
        # Title (required)
        title_val = DatabaseEntryValue(
            entry_id=entry.id,
            property_id=prop_map["Title"].id,
            value={"text": f"Task {i + 1}"},
        )
        test_db.add(title_val)
        values.append(title_val)

        # Status
        status_val = DatabaseEntryValue(
            entry_id=entry.id,
            property_id=prop_map["Status"].id,
            value={"select": {"name": ["To Do", "In Progress", "Done"][i % 3], "color": "#6B7280"}},
        )
        test_db.add(status_val)
        values.append(status_val)

    await test_db.flush()
    for val in values:
        await test_db.refresh(val)

    return values


@pytest_asyncio.fixture
async def sample_template(
    test_db: AsyncSession,
    sample_project: Project,
    sample_user: User,
) -> Database:
    """Create sample template database."""
    template = Database(
        project_id=sample_project.id,
        name="Bug Tracker Template",
        description="Template for bugs",
        icon="🐛",
        color="#EF4444",
        is_template=True,
        created_by_user_id=sample_user.id,
    )
    test_db.add(template)
    await test_db.flush()

    # Add properties
    props = [
        DatabaseProperty(
            database_id=template.id,
            name="Bug Title",
            property_type="text",
            config={},
            position=0,
            is_required=True,
            is_visible=True,
        ),
        DatabaseProperty(
            database_id=template.id,
            name="Severity",
            property_type="select",
            config={"options": [{"name": "High", "color": "#EF4444"}]},
            position=1,
            is_required=False,
            is_visible=True,
        ),
    ]
    for p in props:
        test_db.add(p)

    # Add view
    view = DatabaseView(
        database_id=template.id,
        name="All Bugs",
        view_type="table",
        config={},
        position=0,
        is_default=True,
        created_by_user_id=sample_user.id,
    )
    test_db.add(view)

    await test_db.flush()
    await test_db.refresh(template)
    return template


@pytest_asyncio.fixture
async def sample_formula_property(
    test_db: AsyncSession,
    sample_database: Database,
    sample_properties: List[DatabaseProperty],
) -> DatabaseProperty:
    """Create sample formula property."""
    status_prop = next(p for p in sample_properties if p.name == "Status")

    formula_prop = DatabaseProperty(
        database_id=sample_database.id,
        name="Progress",
        property_type="formula",
        config={
            "formula": f"if(prop('{status_prop.id}') == 'Done', 100, 0)",
            "result_type": "number",
        },
        position=10,
        is_required=False,
        is_visible=True,
    )

    test_db.add(formula_prop)
    await test_db.flush()
    await test_db.refresh(formula_prop)
    return formula_prop


@pytest_asyncio.fixture
async def database_with_relations(
    test_db: AsyncSession,
    test_project: dict,
    test_user: dict,
) -> Database:
    """Create database with relation property using test_user's project."""
    database = Database(
        project_id=UUID(test_project["id"]),
        name="Related Tasks",
        icon="🔗",
        color="#8B5CF6",
        created_by_user_id=UUID(test_user["user"]["id"]),
    )
    test_db.add(database)
    await test_db.flush()

    relation_prop = DatabaseProperty(
        database_id=database.id,
        name="Related Tasks",
        property_type="relation",
        config={"related_database_id": str(database.id)},
        position=0,
        is_required=False,
        is_visible=True,
    )
    test_db.add(relation_prop)
    await test_db.flush()

    await test_db.refresh(database)
    return database


@pytest_asyncio.fixture
async def sample_rollup_property(
    test_db: AsyncSession,
    database_with_relations: Database,
) -> DatabaseProperty:
    """Create sample rollup property."""
    from sqlalchemy import select

    stmt = (
        select(DatabaseProperty)
        .where(DatabaseProperty.database_id == database_with_relations.id)
        .where(DatabaseProperty.property_type == "relation")
    )
    result = await test_db.execute(stmt)
    relation_prop = result.scalar_one()

    count_prop = DatabaseProperty(
        database_id=database_with_relations.id,
        name="Task Count",
        property_type="number",
        config={},
        position=1,
        is_required=False,
        is_visible=True,
    )
    test_db.add(count_prop)
    await test_db.flush()

    rollup_prop = DatabaseProperty(
        database_id=database_with_relations.id,
        name="Related Task Count",
        property_type="rollup",
        config={
            "relation_property_id": str(relation_prop.id),
            "rollup_property_id": str(count_prop.id),
            "aggregation": "count",
        },
        position=2,
        is_required=False,
        is_visible=True,
    )

    test_db.add(rollup_prop)
    await test_db.flush()
    await test_db.refresh(rollup_prop)
    return rollup_prop


@pytest_asyncio.fixture
async def viewer_user(test_db: AsyncSession) -> User:
    """
    Create viewer user for permission testing.

    Returns user with hashed password for authentication.
    """
    user = User(
        id=uuid4(),
        email="viewer@example.com",
        username="viewer",
        password_hash=pwd_context.hash("password123"),
        full_name="Viewer User",
        is_active=True,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest_asyncio.fixture
async def admin_user(test_db: AsyncSession) -> User:
    """
    Create admin user for permission testing.

    Returns user with hashed password for authentication.
    """
    user = User(
        id=uuid4(),
        email="admin@example.com",
        username="admin",
        password_hash=pwd_context.hash("password123"),
        full_name="Admin User",
        is_active=True,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest_asyncio.fixture
async def viewer_member(
    test_db: AsyncSession,
    test_project: dict,
    viewer_user: User,
) -> ProjectMember:
    """
    Add viewer user as viewer member to test project.

    Args:
        test_db: Test database session
        test_project: Test project fixture
        viewer_user: Viewer user fixture

    Returns:
        ProjectMember with viewer role
    """
    member = ProjectMember(
        project_id=UUID(test_project["id"]),
        user_id=viewer_user.id,
        role="viewer",
    )
    test_db.add(member)
    await test_db.commit()
    await test_db.refresh(member)
    return member


@pytest_asyncio.fixture
async def admin_member(
    test_db: AsyncSession,
    test_project: dict,
    admin_user: User,
) -> ProjectMember:
    """
    Add admin user as admin member to test project.

    Args:
        test_db: Test database session
        test_project: Test project fixture
        admin_user: Admin user fixture

    Returns:
        ProjectMember with admin role
    """
    member = ProjectMember(
        project_id=UUID(test_project["id"]),
        user_id=admin_user.id,
        role="admin",
    )
    test_db.add(member)
    await test_db.commit()
    await test_db.refresh(member)
    return member
