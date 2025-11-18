"""
Unit tests for PullRequestRepository.

Tests cover all 18 repository methods including CRUD operations, state management,
task and commit linking, and relationship loading.
"""

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from ardha.models.github_integration import PullRequest
from ardha.repositories.pull_request import PullRequestRepository


@pytest.mark.asyncio
class TestPullRequestRepository:
    """Test suite for PullRequestRepository."""

    async def test_create_pr_success(self, test_db, sample_github_integration, sample_project):
        """Test successful PR creation."""
        repo = PullRequestRepository(test_db)

        pr = PullRequest(
            github_integration_id=sample_github_integration.id,
            project_id=sample_project.id,
            pr_number=123,
            github_pr_id=987654321,
            title="Add new feature",
            description="This PR adds a new feature",
            state="open",
            head_branch="feature/new-feature",
            base_branch="main",
            head_sha="abc123def456",
            author_github_username="octocat",
            html_url="https://github.com/owner/repo/pull/123",
            api_url="https://api.github.com/repos/owner/repo/pulls/123",
        )

        created = await repo.create(pr)

        assert created.id is not None
        assert created.pr_number == 123
        assert created.title == "Add new feature"
        assert created.state == "open"
        assert created.is_draft is False
        assert created.merged is False

    async def test_create_pr_duplicate_number(
        self, test_db, sample_github_integration, sample_project
    ):
        """Test creating PR with duplicate number fails."""
        repo = PullRequestRepository(test_db)

        # Create first PR
        pr1 = PullRequest(
            github_integration_id=sample_github_integration.id,
            project_id=sample_project.id,
            pr_number=100,
            github_pr_id=111,
            title="First PR",
            head_branch="feature-1",
            base_branch="main",
            head_sha="sha1",
            author_github_username="user1",
            html_url="https://github.com/owner/repo/pull/100",
            api_url="https://api.github.com/repos/owner/repo/pulls/100",
        )
        await repo.create(pr1)

        # Try to create second PR with same number
        pr2 = PullRequest(
            github_integration_id=sample_github_integration.id,
            project_id=sample_project.id,
            pr_number=100,
            github_pr_id=222,
            title="Second PR",
            head_branch="feature-2",
            base_branch="main",
            head_sha="sha2",
            author_github_username="user2",
            html_url="https://github.com/owner/repo/pull/100",
            api_url="https://api.github.com/repos/owner/repo/pulls/100",
        )

        with pytest.raises(IntegrityError):
            await repo.create(pr2)

    async def test_get_by_id_success(self, test_db, sample_pull_request):
        """Test fetching PR by ID."""
        repo = PullRequestRepository(test_db)

        pr = await repo.get_by_id(sample_pull_request.id)

        assert pr is not None
        assert pr.id == sample_pull_request.id
        assert pr.pr_number == sample_pull_request.pr_number

    async def test_get_by_id_not_found(self, test_db):
        """Test fetching non-existent PR returns None."""
        repo = PullRequestRepository(test_db)

        pr = await repo.get_by_id(uuid4())

        assert pr is None

    async def test_get_by_number_success(self, test_db, sample_pull_request):
        """Test fetching PR by integration and number."""
        repo = PullRequestRepository(test_db)

        pr = await repo.get_by_number(
            sample_pull_request.github_integration_id,
            sample_pull_request.pr_number,
        )

        assert pr is not None
        assert pr.pr_number == sample_pull_request.pr_number

    async def test_get_by_number_not_found(self, test_db, sample_github_integration):
        """Test fetching non-existent PR by number returns None."""
        repo = PullRequestRepository(test_db)

        pr = await repo.get_by_number(sample_github_integration.id, 999)

        assert pr is None

    async def test_get_by_github_id_success(self, test_db, sample_pull_request):
        """Test fetching PR by GitHub's internal ID."""
        repo = PullRequestRepository(test_db)

        pr = await repo.get_by_github_id(sample_pull_request.github_pr_id)

        assert pr is not None
        assert pr.github_pr_id == sample_pull_request.github_pr_id

    async def test_get_by_github_id_not_found(self, test_db):
        """Test fetching non-existent GitHub PR ID returns None."""
        repo = PullRequestRepository(test_db)

        pr = await repo.get_by_github_id(999999999)

        assert pr is None

    async def test_list_by_project_all(self, test_db, sample_pull_request):
        """Test listing all PRs for a project."""
        repo = PullRequestRepository(test_db)

        prs = await repo.list_by_project(sample_pull_request.project_id)

        assert len(prs) >= 1
        assert sample_pull_request.id in [p.id for p in prs]

    async def test_list_by_project_filtered_by_state(
        self, test_db, sample_github_integration, sample_project
    ):
        """Test listing PRs filtered by state."""
        repo = PullRequestRepository(test_db)

        # Create PRs with different states
        for state in ["open", "closed", "merged"]:
            pr = PullRequest(
                github_integration_id=sample_github_integration.id,
                project_id=sample_project.id,
                pr_number=200 + ord(state[0]),
                github_pr_id=300 + ord(state[0]),
                title=f"PR {state}",
                state=state,
                head_branch=f"feature-{state}",
                base_branch="main",
                head_sha=f"sha-{state}",
                author_github_username="tester",
                html_url=f"https://github.com/owner/repo/pull/{200 + ord(state[0])}",
                api_url=f"https://api.github.com/repos/owner/repo/pulls/{200 + ord(state[0])}",
            )
            await repo.create(pr)

        open_prs = await repo.list_by_project(sample_project.id, state="open")

        assert len(open_prs) == 1
        assert open_prs[0].state == "open"

    async def test_list_by_project_pagination(
        self, test_db, sample_github_integration, sample_project
    ):
        """Test pagination in list_by_project."""
        repo = PullRequestRepository(test_db)

        # Create 5 PRs
        for i in range(5):
            pr = PullRequest(
                github_integration_id=sample_github_integration.id,
                project_id=sample_project.id,
                pr_number=400 + i,
                github_pr_id=500 + i,
                title=f"PR {i}",
                head_branch=f"feature-{i}",
                base_branch="main",
                head_sha=f"sha-{i}",
                author_github_username="dev",
                html_url=f"https://github.com/owner/repo/pull/{400 + i}",
                api_url=f"https://api.github.com/repos/owner/repo/pulls/{400 + i}",
            )
            await repo.create(pr)

        # Test pagination
        page1 = await repo.list_by_project(sample_project.id, skip=0, limit=3)
        page2 = await repo.list_by_project(sample_project.id, skip=3, limit=3)

        assert len(page1) == 3
        assert len(page2) == 2
        # Ensure no overlap
        page1_ids = {p.id for p in page1}
        page2_ids = {p.id for p in page2}
        assert len(page1_ids & page2_ids) == 0

    async def test_list_by_integration_success(self, test_db, sample_pull_request):
        """Test listing PRs by GitHub integration."""
        repo = PullRequestRepository(test_db)

        prs = await repo.list_by_integration(sample_pull_request.github_integration_id)

        assert len(prs) >= 1
        assert sample_pull_request.id in [p.id for p in prs]

    async def test_list_open_prs(self, test_db, sample_github_integration, sample_project):
        """Test listing only open PRs."""
        repo = PullRequestRepository(test_db)

        # Create mix of open and closed PRs
        for i, state in enumerate(["open", "closed", "open"]):
            pr = PullRequest(
                github_integration_id=sample_github_integration.id,
                project_id=sample_project.id,
                pr_number=600 + i,
                github_pr_id=700 + i,
                title=f"PR {state} {i}",
                state=state,
                head_branch=f"branch-{i}",
                base_branch="main",
                head_sha=f"sha-{i}",
                author_github_username="coder",
                html_url=f"https://github.com/owner/repo/pull/{600 + i}",
                api_url=f"https://api.github.com/repos/owner/repo/pulls/{600 + i}",
            )
            await repo.create(pr)

        open_prs = await repo.list_open_prs(sample_project.id)

        assert len(open_prs) == 2
        assert all(p.state == "open" for p in open_prs)

    async def test_update_pr_success(self, test_db, sample_pull_request):
        """Test updating PR fields."""
        repo = PullRequestRepository(test_db)

        update_data = {
            "title": "Updated title",
            "description": "Updated description",
            "is_draft": True,
        }

        updated = await repo.update(sample_pull_request.id, update_data)

        assert updated is not None
        assert updated.title == "Updated title"
        assert updated.description == "Updated description"
        assert updated.is_draft is True

    async def test_update_pr_not_found(self, test_db):
        """Test updating non-existent PR returns None."""
        repo = PullRequestRepository(test_db)

        updated = await repo.update(uuid4(), {"title": "New title"})

        assert updated is None

    async def test_update_from_github_success(self, test_db, sample_pull_request):
        """Test updating PR from GitHub API response."""
        repo = PullRequestRepository(test_db)

        github_data = {
            "title": "GitHub updated title",
            "body": "GitHub updated body",
            "state": "closed",
            "draft": True,
            "mergeable": True,
            "merged": False,
            "additions": 100,
            "deletions": 50,
            "changed_files": 10,
            "commits": 5,
        }

        updated = await repo.update_from_github(sample_pull_request.id, github_data)

        assert updated is not None
        assert updated.title == "GitHub updated title"
        assert updated.description == "GitHub updated body"
        assert updated.state == "closed"
        assert updated.is_draft is True
        assert updated.additions == 100
        assert updated.deletions == 50

    async def test_update_state_merged(self, test_db, sample_pull_request):
        """Test updating PR state to merged with timestamp."""
        repo = PullRequestRepository(test_db)

        merged_time = datetime.now(timezone.utc)

        updated = await repo.update_state(
            sample_pull_request.id,
            "merged",
            merged_at=merged_time,
        )

        assert updated is not None
        assert updated.state == "merged"
        assert updated.merged is True
        assert updated.merged_at == merged_time

    async def test_update_state_closed(self, test_db, sample_pull_request):
        """Test updating PR state to closed with timestamp."""
        repo = PullRequestRepository(test_db)

        closed_time = datetime.now(timezone.utc)

        updated = await repo.update_state(
            sample_pull_request.id,
            "closed",
            closed_at=closed_time,
        )

        assert updated is not None
        assert updated.state == "closed"
        assert updated.closed_at == closed_time

    async def test_update_checks_status_success(self, test_db, sample_pull_request):
        """Test updating CI/CD checks status."""
        repo = PullRequestRepository(test_db)

        updated = await repo.update_checks_status(
            sample_pull_request.id,
            checks_status="success",
            checks_count=5,
            required_checks_passed=True,
        )

        assert updated is not None
        assert updated.checks_status == "success"
        assert updated.checks_count == 5
        assert updated.required_checks_passed is True

    async def test_update_checks_status_failure(self, test_db, sample_pull_request):
        """Test updating checks status to failure."""
        repo = PullRequestRepository(test_db)

        updated = await repo.update_checks_status(
            sample_pull_request.id,
            checks_status="failure",
            checks_count=3,
            required_checks_passed=False,
        )

        assert updated is not None
        assert updated.checks_status == "failure"
        assert updated.required_checks_passed is False

    async def test_update_review_status_approved(self, test_db, sample_pull_request):
        """Test updating review status to approved."""
        repo = PullRequestRepository(test_db)

        updated = await repo.update_review_status(
            sample_pull_request.id,
            review_status="approved",
            reviews_count=3,
            approvals_count=2,
        )

        assert updated is not None
        assert updated.review_status == "approved"
        assert updated.reviews_count == 3
        assert updated.approvals_count == 2

    async def test_update_review_status_changes_requested(self, test_db, sample_pull_request):
        """Test updating review status to changes_requested."""
        repo = PullRequestRepository(test_db)

        updated = await repo.update_review_status(
            sample_pull_request.id,
            review_status="changes_requested",
            reviews_count=2,
            approvals_count=0,
        )

        assert updated is not None
        assert updated.review_status == "changes_requested"
        assert updated.approvals_count == 0

    async def test_link_to_tasks_success(self, test_db, sample_pull_request, sample_tasks):
        """Test linking tasks to PR."""
        repo = PullRequestRepository(test_db)

        task_ids = [task.id for task in sample_tasks[:2]]

        await repo.link_to_tasks(
            sample_pull_request.id,
            task_ids,
            link_type="implements",
            linked_from="pr_description",
        )

        # Verify links created
        linked_tasks = await repo.get_linked_tasks(sample_pull_request.id)
        assert len(linked_tasks) == 2
        linked_task_ids = {t.id for t in linked_tasks}
        assert linked_task_ids == set(task_ids)

    async def test_link_to_tasks_empty_list(self, test_db, sample_pull_request):
        """Test linking empty task list does nothing."""
        repo = PullRequestRepository(test_db)

        # Should not raise error
        await repo.link_to_tasks(sample_pull_request.id, [])

        linked_tasks = await repo.get_linked_tasks(sample_pull_request.id)
        assert len(linked_tasks) == 0

    async def test_link_to_tasks_duplicate_graceful(
        self, test_db, sample_pull_request, sample_tasks
    ):
        """Test linking duplicate tasks is handled gracefully."""
        repo = PullRequestRepository(test_db)

        task_id = sample_tasks[0].id

        # Link first time
        await repo.link_to_tasks(sample_pull_request.id, [task_id])

        # Link again (should not raise error)
        await repo.link_to_tasks(sample_pull_request.id, [task_id])

        # Should still have only one link
        linked_tasks = await repo.get_linked_tasks(sample_pull_request.id)
        assert len(linked_tasks) == 1

    async def test_link_to_commits_success(self, test_db, sample_pull_request, sample_git_commits):
        """Test linking commits to PR with position ordering."""
        repo = PullRequestRepository(test_db)

        commit_ids = [commit.id for commit in sample_git_commits[:3]]

        await repo.link_to_commits(sample_pull_request.id, commit_ids)

        # Verify links created in order
        linked_commits = await repo.get_linked_commits(sample_pull_request.id)
        assert len(linked_commits) == 3
        # Commits should be in same order as input
        for i, commit in enumerate(linked_commits):
            assert commit.id == commit_ids[i]

    async def test_link_to_commits_empty_list(self, test_db, sample_pull_request):
        """Test linking empty commit list does nothing."""
        repo = PullRequestRepository(test_db)

        await repo.link_to_commits(sample_pull_request.id, [])

        linked_commits = await repo.get_linked_commits(sample_pull_request.id)
        assert len(linked_commits) == 0

    async def test_get_linked_tasks(self, test_db, sample_pull_request, sample_tasks):
        """Test retrieving linked tasks."""
        repo = PullRequestRepository(test_db)

        # Link tasks
        task_ids = [task.id for task in sample_tasks]
        await repo.link_to_tasks(sample_pull_request.id, task_ids)

        # Fetch linked tasks
        linked_tasks = await repo.get_linked_tasks(sample_pull_request.id)

        assert len(linked_tasks) == len(sample_tasks)

    async def test_get_linked_tasks_empty(self, test_db, sample_pull_request):
        """Test getting linked tasks when none exist."""
        repo = PullRequestRepository(test_db)

        linked_tasks = await repo.get_linked_tasks(sample_pull_request.id)

        assert len(linked_tasks) == 0

    async def test_get_linked_commits(self, test_db, sample_pull_request, sample_git_commits):
        """Test retrieving linked commits in order."""
        repo = PullRequestRepository(test_db)

        # Link commits
        commit_ids = [commit.id for commit in sample_git_commits]
        await repo.link_to_commits(sample_pull_request.id, commit_ids)

        # Fetch linked commits
        linked_commits = await repo.get_linked_commits(sample_pull_request.id)

        assert len(linked_commits) == len(sample_git_commits)

    async def test_get_linked_commits_empty(self, test_db, sample_pull_request):
        """Test getting linked commits when none exist."""
        repo = PullRequestRepository(test_db)

        linked_commits = await repo.get_linked_commits(sample_pull_request.id)

        assert len(linked_commits) == 0

    async def test_count_by_project_all(self, test_db, sample_pull_request):
        """Test counting all PRs for a project."""
        repo = PullRequestRepository(test_db)

        count = await repo.count_by_project(sample_pull_request.project_id)

        assert count >= 1

    async def test_count_by_project_filtered(
        self, test_db, sample_github_integration, sample_project
    ):
        """Test counting PRs filtered by state."""
        repo = PullRequestRepository(test_db)

        # Create PRs with different states
        states = ["open", "open", "closed", "merged"]
        for i, state in enumerate(states):
            pr = PullRequest(
                github_integration_id=sample_github_integration.id,
                project_id=sample_project.id,
                pr_number=800 + i,
                github_pr_id=900 + i,
                title=f"Count PR {i}",
                state=state,
                head_branch=f"count-{i}",
                base_branch="main",
                head_sha=f"count-sha-{i}",
                author_github_username="counter",
                html_url=f"https://github.com/owner/repo/pull/{800 + i}",
                api_url=f"https://api.github.com/repos/owner/repo/pulls/{800 + i}",
            )
            await repo.create(pr)

        open_count = await repo.count_by_project(sample_project.id, state="open")

        assert open_count == 2

    async def test_get_pr_with_full_details(
        self, test_db, sample_pull_request, sample_tasks, sample_git_commits
    ):
        """Test fetching PR with all relationships loaded."""
        repo = PullRequestRepository(test_db)

        # Link tasks and commits
        task_ids = [task.id for task in sample_tasks[:2]]
        commit_ids = [commit.id for commit in sample_git_commits[:2]]
        await repo.link_to_tasks(sample_pull_request.id, task_ids)
        await repo.link_to_commits(sample_pull_request.id, commit_ids)

        # Fetch full details
        result = await repo.get_pr_with_full_details(sample_pull_request.id)

        assert result is not None
        pr, tasks, commits = result

        assert pr.id == sample_pull_request.id
        assert len(tasks) == 2
        assert len(commits) == 2

    async def test_get_pr_with_full_details_not_found(self, test_db):
        """Test fetching full details for non-existent PR returns None."""
        repo = PullRequestRepository(test_db)

        result = await repo.get_pr_with_full_details(uuid4())

        assert result is None
