"""
GitHub API Client Service.

Provides async-compatible wrapper around PyGithub for all GitHub operations.
Includes authentication, PR management, webhooks, and commit operations.
"""

import asyncio
import logging
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Any, Dict, List, Optional

from cryptography.fernet import Fernet
from github import Github, GithubException

from ardha.core.github_exceptions import (
    GitHubAPIError,
    GitHubAuthenticationError,
    GitHubPermissionError,
    GitHubPullRequestError,
    GitHubRateLimitError,
    GitHubRepositoryNotFoundError,
    GitHubWebhookError,
)

logger = logging.getLogger(__name__)


class TokenEncryption:
    """Utility class for encrypting/decrypting GitHub tokens."""

    @staticmethod
    def get_encryption_key() -> bytes:
        """
        Get encryption key from environment.

        Returns:
            Encryption key as bytes

        Raises:
            ValueError: If GITHUB_TOKEN_ENCRYPTION_KEY not set
        """
        key = os.getenv("GITHUB_TOKEN_ENCRYPTION_KEY")
        if not key:
            raise ValueError("GITHUB_TOKEN_ENCRYPTION_KEY not set in environment")
        return key.encode()

    @staticmethod
    def encrypt_token(token: str) -> str:
        """
        Encrypt GitHub token for secure storage.

        Args:
            token: Plain text GitHub token

        Returns:
            Encrypted token string
        """
        f = Fernet(TokenEncryption.get_encryption_key())
        encrypted = f.encrypt(token.encode())
        return encrypted.decode()

    @staticmethod
    def decrypt_token(encrypted_token: str) -> str:
        """
        Decrypt GitHub token for API usage.

        Args:
            encrypted_token: Encrypted token string

        Returns:
            Plain text GitHub token
        """
        f = Fernet(TokenEncryption.get_encryption_key())
        decrypted = f.decrypt(encrypted_token.encode())
        return decrypted.decode()


class GitHubAPIClient:
    """
    Async-compatible GitHub API client using PyGithub.

    Provides clean interface for all GitHub operations including:
    - Authentication and repository access
    - Pull request operations
    - Webhook management
    - Commit and status operations
    """

    def __init__(self, access_token: str, base_url: str = "https://api.github.com"):
        """
        Initialize GitHub API client.

        Args:
            access_token: GitHub personal access token or OAuth token
            base_url: GitHub API base URL (for GitHub Enterprise)
        """
        self._token = access_token
        self._base_url = base_url
        self._client: Optional[Github] = None
        self._executor = ThreadPoolExecutor(max_workers=4)

    @property
    def client(self) -> Github:
        """
        Lazy-load GitHub client.

        Returns:
            Configured Github instance
        """
        if self._client is None:
            self._client = Github(self._token, base_url=self._base_url)
        return self._client

    async def _run_sync(self, func, *args, **kwargs):
        """
        Run synchronous PyGithub operation in executor.

        Args:
            func: Synchronous function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Function result
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self._executor, func, *args, **kwargs)

    def _handle_github_exception(self, e: GithubException) -> None:
        """
        Convert PyGithub exceptions to custom exceptions.

        Args:
            e: GithubException from PyGithub

        Raises:
            GitHubAuthenticationError: For 401/403 authentication errors
            GitHubRateLimitError: For 429 rate limit errors
            GitHubRepositoryNotFoundError: For 404 repository errors
            GitHubPullRequestError: For PR-related errors
            GitHubPermissionError: For 422 permission errors
            GitHubAPIError: For other API errors
        """
        status_code = e.status

        # Authentication errors (401, 403)
        if status_code in (401, 403):
            raise GitHubAuthenticationError(
                f"GitHub authentication failed: {e.data.get('message', str(e))}",
                status_code=status_code,
            )

        # Rate limiting (429)
        if status_code == 429:
            # Extract rate limit reset time from headers
            reset_at = None
            if hasattr(e, "headers") and e.headers and "X-RateLimit-Reset" in e.headers:
                reset_timestamp = int(e.headers["X-RateLimit-Reset"])
                reset_at = datetime.fromtimestamp(reset_timestamp)

            raise GitHubRateLimitError(
                f"GitHub rate limit exceeded: {e.data.get('message', str(e))}",
                reset_at=reset_at,
            )

        # Not found errors (404)
        if status_code == 404:
            error_msg = e.data.get("message", str(e))
            # Determine if it's a repository or PR error based on message
            if "pull request" in error_msg.lower() or "pr" in error_msg.lower():
                raise GitHubPullRequestError(f"Pull request not found: {error_msg}")
            else:
                raise GitHubRepositoryNotFoundError(f"Repository not found: {error_msg}")

        # Permission/validation errors (422)
        if status_code == 422:
            raise GitHubPermissionError(
                f"GitHub permission denied or validation failed: {e.data.get('message', str(e))}"
            )

        # Generic API error
        raise GitHubAPIError(
            f"GitHub API error: {e.data.get('message', str(e))}",
            status_code=status_code,
            response=e.data if hasattr(e, "data") else None,
        )

    # ============= Authentication & Repository Methods =============

    async def verify_token(self) -> Dict[str, Any]:
        """
        Verify GitHub token is valid and get user information.

        Returns:
            Dict with authenticated user data and token scopes:
            {
                "login": str,
                "name": str,
                "email": str,
                "avatar_url": str,
                "scopes": list[str]
            }

        Raises:
            GitHubAuthenticationError: If token is invalid
        """
        try:

            def _verify():
                user = self.client.get_user()
                # Get token scopes from requester
                scopes = getattr(self.client, "_Github__requester", None)
                scope_list = []
                if scopes and hasattr(scopes, "oauth_scopes"):
                    scope_list = scopes.oauth_scopes

                return {
                    "login": user.login,
                    "name": user.name or user.login,
                    "email": user.email or "",
                    "avatar_url": user.avatar_url,
                    "scopes": scope_list,
                }

            result = await self._run_sync(_verify)
            logger.info(f"GitHub token verified for user: {result['login']}")
            return result

        except GithubException as e:
            self._handle_github_exception(e)
            raise  # For type checker
        except Exception as e:
            logger.error(f"Unexpected error verifying GitHub token: {e}")
            raise GitHubAPIError(f"Failed to verify token: {e}")

    async def get_repository(self, owner: str, repo: str) -> Dict[str, Any]:
        """
        Get repository information.

        Args:
            owner: Repository owner (username or organization)
            repo: Repository name

        Returns:
            Dict with repository data:
            {
                "name": str,
                "full_name": str,
                "description": str,
                "url": str,
                "default_branch": str,
                "private": bool,
                "fork": bool,
                "archived": bool
            }

        Raises:
            GitHubRepositoryNotFoundError: If repository doesn't exist
        """
        try:

            def _get_repo():
                repository = self.client.get_repo(f"{owner}/{repo}")
                return {
                    "name": repository.name,
                    "full_name": repository.full_name,
                    "description": repository.description or "",
                    "url": repository.html_url,
                    "clone_url": repository.clone_url,
                    "default_branch": repository.default_branch,
                    "private": repository.private,
                    "fork": repository.fork,
                    "archived": repository.archived,
                    "created_at": (
                        repository.created_at.isoformat() if repository.created_at else None
                    ),
                    "updated_at": (
                        repository.updated_at.isoformat() if repository.updated_at else None
                    ),
                }

            result = await self._run_sync(_get_repo)
            logger.info(f"Retrieved repository: {owner}/{repo}")
            return result

        except GithubException as e:
            self._handle_github_exception(e)
            raise  # For type checker
        except Exception as e:
            logger.error(f"Unexpected error getting repository {owner}/{repo}: {e}")
            raise GitHubAPIError(f"Failed to get repository: {e}")

    async def check_repository_access(self, owner: str, repo: str) -> bool:
        """
        Check if token has access to repository.

        Args:
            owner: Repository owner
            repo: Repository name

        Returns:
            True if accessible, False otherwise
        """
        try:

            def _check_access():
                repository = self.client.get_repo(f"{owner}/{repo}")
                # Try to access permissions
                _ = repository.permissions
                return True

            result = await self._run_sync(_check_access)
            logger.info(f"Access check for {owner}/{repo}: {result}")
            return result

        except GithubException:
            logger.info(f"No access to repository {owner}/{repo}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error checking access to {owner}/{repo}: {e}")
            return False

    async def get_repository_branches(self, owner: str, repo: str) -> List[str]:
        """
        List all branches in repository.

        Args:
            owner: Repository owner
            repo: Repository name

        Returns:
            List of branch names

        Raises:
            GitHubRepositoryNotFoundError: If repository doesn't exist
        """
        try:

            def _get_branches():
                repository = self.client.get_repo(f"{owner}/{repo}")
                return [branch.name for branch in repository.get_branches()]

            result = await self._run_sync(_get_branches)
            logger.info(f"Retrieved {len(result)} branches from {owner}/{repo}")
            return result

        except GithubException as e:
            self._handle_github_exception(e)
            raise  # For type checker
        except Exception as e:
            logger.error(f"Unexpected error getting branches for {owner}/{repo}: {e}")
            raise GitHubAPIError(f"Failed to get branches: {e}")

    async def get_default_branch(self, owner: str, repo: str) -> str:
        """
        Get repository default branch.

        Args:
            owner: Repository owner
            repo: Repository name

        Returns:
            Default branch name (usually 'main' or 'master')

        Raises:
            GitHubRepositoryNotFoundError: If repository doesn't exist
        """
        try:

            def _get_default():
                repository = self.client.get_repo(f"{owner}/{repo}")
                return repository.default_branch

            result = await self._run_sync(_get_default)
            logger.info(f"Default branch for {owner}/{repo}: {result}")
            return result

        except GithubException as e:
            self._handle_github_exception(e)
            raise  # For type checker
        except Exception as e:
            logger.error(f"Unexpected error getting default branch for {owner}/{repo}: {e}")
            raise GitHubAPIError(f"Failed to get default branch: {e}")

    # ============= Pull Request Operations =============

    async def create_pull_request(
        self,
        owner: str,
        repo: str,
        title: str,
        body: str,
        head: str,
        base: str,
        draft: bool = False,
    ) -> Dict[str, Any]:
        """
        Create new pull request.

        Args:
            owner: Repository owner
            repo: Repository name
            title: PR title
            body: PR description
            head: Source branch
            base: Target branch
            draft: Create as draft PR

        Returns:
            Dict with PR data including number, url, id

        Raises:
            GitHubPullRequestError: If PR creation fails
        """
        try:

            def _create_pr():
                repository = self.client.get_repo(f"{owner}/{repo}")
                pr = repository.create_pull(
                    title=title,
                    body=body,
                    head=head,
                    base=base,
                    draft=draft,
                )
                return {
                    "number": pr.number,
                    "id": pr.id,
                    "title": pr.title,
                    "body": pr.body,
                    "state": pr.state,
                    "html_url": pr.html_url,
                    "api_url": pr.url,
                    "head_branch": pr.head.ref,
                    "base_branch": pr.base.ref,
                    "head_sha": pr.head.sha,
                    "draft": pr.draft,
                    "created_at": pr.created_at.isoformat() if pr.created_at else None,
                }

            result = await self._run_sync(_create_pr)
            logger.info(f"Created PR #{result['number']} in {owner}/{repo}: {title}")
            return result

        except GithubException as e:
            logger.error(f"Failed to create PR in {owner}/{repo}: {e}")
            self._handle_github_exception(e)
            raise  # For type checker
        except Exception as e:
            logger.error(f"Unexpected error creating PR in {owner}/{repo}: {e}")
            raise GitHubPullRequestError(f"Failed to create pull request: {e}", operation="create")

    async def get_pull_request(self, owner: str, repo: str, pr_number: int) -> Dict[str, Any]:
        """
        Get pull request details.

        Args:
            owner: Repository owner
            repo: Repository name
            pr_number: PR number

        Returns:
            Dict with full PR data

        Raises:
            GitHubPullRequestError: If PR not found
        """
        try:

            def _get_pr():
                repository = self.client.get_repo(f"{owner}/{repo}")
                pr = repository.get_pull(pr_number)
                return {
                    "number": pr.number,
                    "id": pr.id,
                    "title": pr.title,
                    "body": pr.body or "",
                    "state": pr.state,
                    "html_url": pr.html_url,
                    "api_url": pr.url,
                    "head_branch": pr.head.ref,
                    "base_branch": pr.base.ref,
                    "head_sha": pr.head.sha,
                    "draft": pr.draft,
                    "mergeable": pr.mergeable,
                    "merged": pr.merged,
                    "merged_at": pr.merged_at.isoformat() if pr.merged_at else None,
                    "closed_at": pr.closed_at.isoformat() if pr.closed_at else None,
                    "additions": pr.additions,
                    "deletions": pr.deletions,
                    "changed_files": pr.changed_files,
                    "commits": pr.commits,
                    "author": pr.user.login if pr.user else None,
                    "created_at": pr.created_at.isoformat() if pr.created_at else None,
                    "updated_at": pr.updated_at.isoformat() if pr.updated_at else None,
                }

            result = await self._run_sync(_get_pr)
            logger.info(f"Retrieved PR #{pr_number} from {owner}/{repo}")
            return result

        except GithubException as e:
            self._handle_github_exception(e)
            raise  # For type checker
        except Exception as e:
            logger.error(f"Unexpected error getting PR #{pr_number} from {owner}/{repo}: {e}")
            raise GitHubPullRequestError(
                f"Failed to get pull request: {e}",
                pr_number=pr_number,
                operation="get",
            )

    async def list_pull_requests(
        self,
        owner: str,
        repo: str,
        state: str = "open",
        base: Optional[str] = None,
        sort: str = "created",
        direction: str = "desc",
    ) -> List[Dict[str, Any]]:
        """
        List pull requests with filters.

        Args:
            owner: Repository owner
            repo: Repository name
            state: PR state ('open', 'closed', 'all')
            base: Filter by base branch
            sort: Sort by ('created', 'updated', 'popularity')
            direction: Sort direction ('asc', 'desc')

        Returns:
            List of PR data dicts

        Raises:
            GitHubRepositoryNotFoundError: If repository doesn't exist
        """
        try:

            def _list_prs():
                repository = self.client.get_repo(f"{owner}/{repo}")
                # PyGithub's get_pulls doesn't accept None for base, so filter afterwards
                prs = repository.get_pulls(
                    state=state,
                    sort=sort,
                    direction=direction,
                )

                # Filter by base if provided
                if base:
                    prs = [pr for pr in prs if pr.base.ref == base]
                else:
                    prs = list(prs)

                result = []
                for pr in prs:
                    result.append(
                        {
                            "number": pr.number,
                            "id": pr.id,
                            "title": pr.title,
                            "state": pr.state,
                            "html_url": pr.html_url,
                            "head_branch": pr.head.ref,
                            "base_branch": pr.base.ref,
                            "draft": pr.draft,
                            "author": pr.user.login if pr.user else None,
                            "created_at": pr.created_at.isoformat() if pr.created_at else None,
                        }
                    )

                return result

            result = await self._run_sync(_list_prs)
            logger.info(f"Listed {len(result)} PRs from {owner}/{repo} (state={state})")
            return result

        except GithubException as e:
            self._handle_github_exception(e)
            raise  # For type checker
        except Exception as e:
            logger.error(f"Unexpected error listing PRs for {owner}/{repo}: {e}")
            raise GitHubPullRequestError(f"Failed to list pull requests: {e}", operation="list")

    async def update_pull_request(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        title: Optional[str] = None,
        body: Optional[str] = None,
        state: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Update pull request title, description, or state.

        Args:
            owner: Repository owner
            repo: Repository name
            pr_number: PR number
            title: New PR title
            body: New PR description
            state: New state ('open' or 'closed')

        Returns:
            Updated PR data

        Raises:
            GitHubPullRequestError: If update fails
        """
        try:

            def _update_pr():
                repository = self.client.get_repo(f"{owner}/{repo}")
                pr = repository.get_pull(pr_number)

                # Update fields
                if title is not None:
                    pr.edit(title=title)
                if body is not None:
                    pr.edit(body=body)
                if state is not None:
                    pr.edit(state=state)

                # Refresh PR data
                pr = repository.get_pull(pr_number)

                return {
                    "number": pr.number,
                    "id": pr.id,
                    "title": pr.title,
                    "body": pr.body or "",
                    "state": pr.state,
                    "html_url": pr.html_url,
                    "updated_at": pr.updated_at.isoformat() if pr.updated_at else None,
                }

            result = await self._run_sync(_update_pr)
            logger.info(f"Updated PR #{pr_number} in {owner}/{repo}")
            return result

        except GithubException as e:
            self._handle_github_exception(e)
            raise  # For type checker
        except Exception as e:
            logger.error(f"Unexpected error updating PR #{pr_number} in {owner}/{repo}: {e}")
            raise GitHubPullRequestError(
                f"Failed to update pull request: {e}",
                pr_number=pr_number,
                operation="update",
            )

    async def merge_pull_request(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        commit_message: Optional[str] = None,
        merge_method: str = "merge",
    ) -> Dict[str, Any]:
        """
        Merge pull request.

        Args:
            owner: Repository owner
            repo: Repository name
            pr_number: PR number
            commit_message: Optional merge commit message
            merge_method: 'merge', 'squash', or 'rebase'

        Returns:
            Merge result data

        Raises:
            GitHubPullRequestError: If PR is not mergeable or merge fails
        """
        try:

            def _merge_pr():
                repository = self.client.get_repo(f"{owner}/{repo}")
                pr = repository.get_pull(pr_number)

                # Check if mergeable
                if pr.mergeable is False:
                    raise GitHubPullRequestError(
                        f"PR #{pr_number} is not mergeable",
                        pr_number=pr_number,
                        operation="merge",
                    )

                # Merge PR
                if commit_message:
                    merge_result = pr.merge(
                        commit_message=commit_message,
                        merge_method=merge_method,
                    )
                else:
                    merge_result = pr.merge(merge_method=merge_method)

                return {
                    "merged": merge_result.merged,
                    "sha": merge_result.sha,
                    "message": merge_result.message,
                }

            result = await self._run_sync(_merge_pr)
            logger.info(f"Merged PR #{pr_number} in {owner}/{repo} using {merge_method}")
            return result

        except GitHubPullRequestError:
            raise
        except GithubException as e:
            self._handle_github_exception(e)
            raise  # For type checker
        except Exception as e:
            logger.error(f"Unexpected error merging PR #{pr_number} in {owner}/{repo}: {e}")
            raise GitHubPullRequestError(
                f"Failed to merge pull request: {e}",
                pr_number=pr_number,
                operation="merge",
            )

    async def get_pr_commits(self, owner: str, repo: str, pr_number: int) -> List[Dict[str, Any]]:
        """
        Get all commits in pull request.

        Args:
            owner: Repository owner
            repo: Repository name
            pr_number: PR number

        Returns:
            List of commit data dicts

        Raises:
            GitHubPullRequestError: If PR not found
        """
        try:

            def _get_commits():
                repository = self.client.get_repo(f"{owner}/{repo}")
                pr = repository.get_pull(pr_number)

                result = []
                for commit in pr.get_commits():
                    result.append(
                        {
                            "sha": commit.sha,
                            "message": commit.commit.message,
                            "author": commit.commit.author.name if commit.commit.author else None,
                            "author_email": (
                                commit.commit.author.email if commit.commit.author else None
                            ),
                            "date": (
                                commit.commit.author.date.isoformat()
                                if commit.commit.author
                                else None
                            ),
                        }
                    )

                return result

            result = await self._run_sync(_get_commits)
            logger.info(f"Retrieved {len(result)} commits from PR #{pr_number} in {owner}/{repo}")
            return result

        except GithubException as e:
            self._handle_github_exception(e)
            raise  # For type checker
        except Exception as e:
            logger.error(f"Unexpected error getting commits for PR #{pr_number}: {e}")
            raise GitHubPullRequestError(
                f"Failed to get PR commits: {e}",
                pr_number=pr_number,
                operation="get_commits",
            )

    async def get_pr_files(self, owner: str, repo: str, pr_number: int) -> List[Dict[str, Any]]:
        """
        Get files changed in pull request.

        Args:
            owner: Repository owner
            repo: Repository name
            pr_number: PR number

        Returns:
            List of file change data

        Raises:
            GitHubPullRequestError: If PR not found
        """
        try:

            def _get_files():
                repository = self.client.get_repo(f"{owner}/{repo}")
                pr = repository.get_pull(pr_number)

                result = []
                for file in pr.get_files():
                    result.append(
                        {
                            "filename": file.filename,
                            "status": file.status,
                            "additions": file.additions,
                            "deletions": file.deletions,
                            "changes": file.changes,
                            "patch": file.patch or "",
                        }
                    )

                return result

            result = await self._run_sync(_get_files)
            logger.info(f"Retrieved {len(result)} files from PR #{pr_number} in {owner}/{repo}")
            return result

        except GithubException as e:
            self._handle_github_exception(e)
            raise  # For type checker
        except Exception as e:
            logger.error(f"Unexpected error getting files for PR #{pr_number}: {e}")
            raise GitHubPullRequestError(
                f"Failed to get PR files: {e}",
                pr_number=pr_number,
                operation="get_files",
            )

    async def get_pr_reviews(self, owner: str, repo: str, pr_number: int) -> List[Dict[str, Any]]:
        """
        Get pull request reviews.

        Args:
            owner: Repository owner
            repo: Repository name
            pr_number: PR number

        Returns:
            List of review data

        Raises:
            GitHubPullRequestError: If PR not found
        """
        try:

            def _get_reviews():
                repository = self.client.get_repo(f"{owner}/{repo}")
                pr = repository.get_pull(pr_number)

                result = []
                for review in pr.get_reviews():
                    result.append(
                        {
                            "id": review.id,
                            "user": review.user.login if review.user else None,
                            "state": review.state,
                            "body": review.body or "",
                            "submitted_at": (
                                review.submitted_at.isoformat() if review.submitted_at else None
                            ),
                        }
                    )

                return result

            result = await self._run_sync(_get_reviews)
            logger.info(f"Retrieved {len(result)} reviews from PR #{pr_number} in {owner}/{repo}")
            return result

        except GithubException as e:
            self._handle_github_exception(e)
            raise  # For type checker
        except Exception as e:
            logger.error(f"Unexpected error getting reviews for PR #{pr_number}: {e}")
            raise GitHubPullRequestError(
                f"Failed to get PR reviews: {e}",
                pr_number=pr_number,
                operation="get_reviews",
            )

    async def get_pr_checks(self, owner: str, repo: str, pr_number: int) -> Dict[str, Any]:
        """
        Get pull request check runs (CI/CD status).

        Args:
            owner: Repository owner
            repo: Repository name
            pr_number: PR number

        Returns:
            Dict with check run data

        Raises:
            GitHubPullRequestError: If PR not found
        """
        try:

            def _get_checks():
                repository = self.client.get_repo(f"{owner}/{repo}")
                pr = repository.get_pull(pr_number)

                # Get check runs for the head SHA
                commit = repository.get_commit(pr.head.sha)
                check_runs = commit.get_check_runs()

                checks = []
                for check in check_runs:
                    checks.append(
                        {
                            "id": check.id,
                            "name": check.name,
                            "status": check.status,
                            "conclusion": check.conclusion,
                            "started_at": (
                                check.started_at.isoformat() if check.started_at else None
                            ),
                            "completed_at": (
                                check.completed_at.isoformat() if check.completed_at else None
                            ),
                        }
                    )

                return {
                    "total_count": check_runs.totalCount,
                    "checks": checks,
                }

            result = await self._run_sync(_get_checks)
            logger.info(
                f"Retrieved {result['total_count']} checks from PR #{pr_number} in {owner}/{repo}"
            )
            return result

        except GithubException as e:
            self._handle_github_exception(e)
            raise  # For type checker
        except Exception as e:
            logger.error(f"Unexpected error getting checks for PR #{pr_number}: {e}")
            raise GitHubPullRequestError(
                f"Failed to get PR checks: {e}",
                pr_number=pr_number,
                operation="get_checks",
            )

    async def add_pr_comment(
        self, owner: str, repo: str, pr_number: int, body: str
    ) -> Dict[str, Any]:
        """
        Add comment to pull request.

        Args:
            owner: Repository owner
            repo: Repository name
            pr_number: PR number
            body: Comment text

        Returns:
            Comment data

        Raises:
            GitHubPullRequestError: If commenting fails
        """
        try:

            def _add_comment():
                repository = self.client.get_repo(f"{owner}/{repo}")
                pr = repository.get_pull(pr_number)
                comment = pr.create_issue_comment(body)

                return {
                    "id": comment.id,
                    "body": comment.body,
                    "user": comment.user.login if comment.user else None,
                    "created_at": comment.created_at.isoformat() if comment.created_at else None,
                }

            result = await self._run_sync(_add_comment)
            logger.info(f"Added comment to PR #{pr_number} in {owner}/{repo}")
            return result

        except GithubException as e:
            self._handle_github_exception(e)
            raise  # For type checker
        except Exception as e:
            logger.error(f"Unexpected error adding comment to PR #{pr_number}: {e}")
            raise GitHubPullRequestError(
                f"Failed to add PR comment: {e}",
                pr_number=pr_number,
                operation="add_comment",
            )

    # ============= Webhook Operations =============

    async def create_webhook(
        self,
        owner: str,
        repo: str,
        webhook_url: str,
        events: List[str],
        secret: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create repository webhook.

        Args:
            owner: Repository owner
            repo: Repository name
            webhook_url: Webhook callback URL
            events: List of events (e.g., ['pull_request', 'push'])
            secret: Optional secret for signature verification

        Returns:
            Webhook data including id, url, events

        Raises:
            GitHubWebhookError: If webhook creation fails
        """
        try:

            def _create_webhook():
                repository = self.client.get_repo(f"{owner}/{repo}")

                config = {
                    "url": webhook_url,
                    "content_type": "json",
                }
                if secret:
                    config["secret"] = secret

                hook = repository.create_hook(
                    name="web",
                    config=config,
                    events=events,
                    active=True,
                )

                return {
                    "id": hook.id,
                    "url": hook.config.get("url"),
                    "events": hook.events,
                    "active": hook.active,
                    "created_at": hook.created_at.isoformat() if hook.created_at else None,
                }

            result = await self._run_sync(_create_webhook)
            logger.info(f"Created webhook for {owner}/{repo} with {len(events)} events")
            return result

        except GithubException as e:
            logger.error(f"Failed to create webhook for {owner}/{repo}: {e}")
            self._handle_github_exception(e)
            raise  # For type checker
        except Exception as e:
            logger.error(f"Unexpected error creating webhook for {owner}/{repo}: {e}")
            raise GitHubWebhookError(f"Failed to create webhook: {e}", operation="create")

    async def list_webhooks(self, owner: str, repo: str) -> List[Dict[str, Any]]:
        """
        List all repository webhooks.

        Args:
            owner: Repository owner
            repo: Repository name

        Returns:
            List of webhook data

        Raises:
            GitHubRepositoryNotFoundError: If repository doesn't exist
        """
        try:

            def _list_webhooks():
                repository = self.client.get_repo(f"{owner}/{repo}")

                result = []
                for hook in repository.get_hooks():
                    result.append(
                        {
                            "id": hook.id,
                            "url": hook.config.get("url"),
                            "events": hook.events,
                            "active": hook.active,
                            "created_at": hook.created_at.isoformat() if hook.created_at else None,
                        }
                    )

                return result

            result = await self._run_sync(_list_webhooks)
            logger.info(f"Listed {len(result)} webhooks from {owner}/{repo}")
            return result

        except GithubException as e:
            self._handle_github_exception(e)
            raise  # For type checker
        except Exception as e:
            logger.error(f"Unexpected error listing webhooks for {owner}/{repo}: {e}")
            raise GitHubWebhookError(f"Failed to list webhooks: {e}", operation="list")

    async def get_webhook(self, owner: str, repo: str, webhook_id: int) -> Dict[str, Any]:
        """
        Get specific webhook details.

        Args:
            owner: Repository owner
            repo: Repository name
            webhook_id: Webhook ID

        Returns:
            Webhook data

        Raises:
            GitHubWebhookError: If webhook not found
        """
        try:

            def _get_webhook():
                repository = self.client.get_repo(f"{owner}/{repo}")
                hook = repository.get_hook(webhook_id)

                return {
                    "id": hook.id,
                    "url": hook.config.get("url"),
                    "events": hook.events,
                    "active": hook.active,
                    "created_at": hook.created_at.isoformat() if hook.created_at else None,
                    "updated_at": hook.updated_at.isoformat() if hook.updated_at else None,
                }

            result = await self._run_sync(_get_webhook)
            logger.info(f"Retrieved webhook {webhook_id} from {owner}/{repo}")
            return result

        except GithubException as e:
            self._handle_github_exception(e)
            raise  # For type checker
        except Exception as e:
            logger.error(f"Unexpected error getting webhook {webhook_id}: {e}")
            raise GitHubWebhookError(
                f"Failed to get webhook: {e}",
                webhook_id=webhook_id,
                operation="get",
            )

    async def update_webhook(
        self,
        owner: str,
        repo: str,
        webhook_id: int,
        webhook_url: Optional[str] = None,
        events: Optional[List[str]] = None,
        active: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """
        Update webhook configuration.

        Args:
            owner: Repository owner
            repo: Repository name
            webhook_id: Webhook ID
            webhook_url: New webhook URL
            events: New event list
            active: New active status

        Returns:
            Updated webhook data

        Raises:
            GitHubWebhookError: If update fails
        """
        try:

            def _update_webhook():
                repository = self.client.get_repo(f"{owner}/{repo}")
                hook = repository.get_hook(webhook_id)

                # Build edit parameters
                edit_params = {"name": "web", "config": hook.config.copy()}

                # Update URL if provided
                if webhook_url is not None:
                    edit_params["config"]["url"] = webhook_url

                # Update events if provided
                if events is not None:
                    edit_params["events"] = events

                # Update active status if provided
                if active is not None:
                    edit_params["active"] = active

                # Apply edits
                hook.edit(**edit_params)

                # Refresh webhook data
                hook = repository.get_hook(webhook_id)

                return {
                    "id": hook.id,
                    "url": hook.config.get("url"),
                    "events": hook.events,
                    "active": hook.active,
                    "updated_at": hook.updated_at.isoformat() if hook.updated_at else None,
                }

            result = await self._run_sync(_update_webhook)
            logger.info(f"Updated webhook {webhook_id} in {owner}/{repo}")
            return result

        except GithubException as e:
            self._handle_github_exception(e)
            raise  # For type checker
        except Exception as e:
            logger.error(f"Unexpected error updating webhook {webhook_id}: {e}")
            raise GitHubWebhookError(
                f"Failed to update webhook: {e}",
                webhook_id=webhook_id,
                operation="update",
            )

    async def delete_webhook(self, owner: str, repo: str, webhook_id: int) -> None:
        """
        Delete webhook.

        Args:
            owner: Repository owner
            repo: Repository name
            webhook_id: Webhook ID

        Raises:
            GitHubWebhookError: If deletion fails
        """
        try:

            def _delete_webhook():
                repository = self.client.get_repo(f"{owner}/{repo}")
                hook = repository.get_hook(webhook_id)
                hook.delete()

            await self._run_sync(_delete_webhook)
            logger.info(f"Deleted webhook {webhook_id} from {owner}/{repo}")

        except GithubException as e:
            self._handle_github_exception(e)
        except Exception as e:
            logger.error(f"Unexpected error deleting webhook {webhook_id}: {e}")
            raise GitHubWebhookError(
                f"Failed to delete webhook: {e}",
                webhook_id=webhook_id,
                operation="delete",
            )

    # ============= Commit & Status Operations =============

    async def get_commit(self, owner: str, repo: str, sha: str) -> Dict[str, Any]:
        """
        Get commit details.

        Args:
            owner: Repository owner
            repo: Repository name
            sha: Commit SHA

        Returns:
            Commit data including message, author, stats, files

        Raises:
            GitHubRepositoryNotFoundError: If repository or commit not found
        """
        try:

            def _get_commit():
                repository = self.client.get_repo(f"{owner}/{repo}")
                commit = repository.get_commit(sha)

                return {
                    "sha": commit.sha,
                    "message": commit.commit.message,
                    "author": commit.commit.author.name if commit.commit.author else None,
                    "author_email": commit.commit.author.email if commit.commit.author else None,
                    "date": commit.commit.author.date.isoformat() if commit.commit.author else None,
                    "stats": {
                        "additions": commit.stats.additions,
                        "deletions": commit.stats.deletions,
                        "total": commit.stats.total,
                    },
                    "files_count": commit.files.totalCount,
                }

            result = await self._run_sync(_get_commit)
            logger.info(f"Retrieved commit {sha} from {owner}/{repo}")
            return result

        except GithubException as e:
            self._handle_github_exception(e)
            raise  # For type checker
        except Exception as e:
            logger.error(f"Unexpected error getting commit {sha} from {owner}/{repo}: {e}")
            raise GitHubAPIError(f"Failed to get commit: {e}")

    async def create_commit_status(
        self,
        owner: str,
        repo: str,
        sha: str,
        state: str,
        target_url: Optional[str] = None,
        description: Optional[str] = None,
        context: str = "ardha",
    ) -> Dict[str, Any]:
        """
        Create commit status.

        Args:
            owner: Repository owner
            repo: Repository name
            sha: Commit SHA
            state: 'pending', 'success', 'failure', 'error'
            target_url: Optional URL with details
            description: Optional status description
            context: Status identifier (e.g., 'ardha/task-sync')

        Returns:
            Status data

        Raises:
            GitHubRepositoryNotFoundError: If repository or commit not found
        """
        try:

            def _create_status():
                repository = self.client.get_repo(f"{owner}/{repo}")
                commit = repository.get_commit(sha)

                # Build status parameters
                status_params = {"state": state, "context": context}
                if target_url is not None:
                    status_params["target_url"] = target_url
                if description is not None:
                    status_params["description"] = description

                status = commit.create_status(**status_params)

                return {
                    "id": status.id,
                    "state": status.state,
                    "description": status.description or "",
                    "context": status.context,
                    "target_url": status.target_url or "",
                    "created_at": status.created_at.isoformat() if status.created_at else None,
                }

            result = await self._run_sync(_create_status)
            logger.info(f"Created status '{state}' for commit {sha} in {owner}/{repo}")
            return result

        except GithubException as e:
            self._handle_github_exception(e)
            raise  # For type checker
        except Exception as e:
            logger.error(f"Unexpected error creating status for commit {sha}: {e}")
            raise GitHubAPIError(f"Failed to create commit status: {e}")

    async def get_commit_statuses(self, owner: str, repo: str, sha: str) -> List[Dict[str, Any]]:
        """
        Get all statuses for commit.

        Args:
            owner: Repository owner
            repo: Repository name
            sha: Commit SHA

        Returns:
            List of status data

        Raises:
            GitHubRepositoryNotFoundError: If repository or commit not found
        """
        try:

            def _get_statuses():
                repository = self.client.get_repo(f"{owner}/{repo}")
                commit = repository.get_commit(sha)

                result = []
                for status in commit.get_statuses():
                    result.append(
                        {
                            "id": status.id,
                            "state": status.state,
                            "description": status.description or "",
                            "context": status.context,
                            "target_url": status.target_url or "",
                            "created_at": (
                                status.created_at.isoformat() if status.created_at else None
                            ),
                        }
                    )

                return result

            result = await self._run_sync(_get_statuses)
            logger.info(f"Retrieved {len(result)} statuses for commit {sha} in {owner}/{repo}")
            return result

        except GithubException as e:
            self._handle_github_exception(e)
            raise  # For type checker
        except Exception as e:
            logger.error(f"Unexpected error getting statuses for commit {sha}: {e}")
            raise GitHubAPIError(f"Failed to get commit statuses: {e}")

    # ============= User & Rate Limiting =============

    async def get_authenticated_user(self) -> Dict[str, Any]:
        """
        Get current authenticated user information.

        Returns:
            User data including login, name, email, avatar_url

        Raises:
            GitHubAuthenticationError: If authentication fails
        """
        try:

            def _get_user():
                user = self.client.get_user()
                return {
                    "login": user.login,
                    "name": user.name or user.login,
                    "email": user.email or "",
                    "avatar_url": user.avatar_url,
                    "bio": user.bio or "",
                    "company": user.company or "",
                    "location": user.location or "",
                }

            result = await self._run_sync(_get_user)
            logger.info(f"Retrieved authenticated user: {result['login']}")
            return result

        except GithubException as e:
            self._handle_github_exception(e)
            raise  # For type checker
        except Exception as e:
            logger.error(f"Unexpected error getting authenticated user: {e}")
            raise GitHubAuthenticationError(f"Failed to get user: {e}")

    async def get_rate_limit(self) -> Dict[str, Any]:
        """
        Get current rate limit status.

        Returns:
            Rate limit data:
            {
                "limit": int,
                "remaining": int,
                "reset": datetime,
                "used": int
            }

        Raises:
            GitHubAPIError: If rate limit check fails
        """
        try:

            def _get_rate_limit():
                rate_limit = self.client.get_rate_limit()
                # Access core rate limit using attribute access
                core_rate = getattr(rate_limit, "core")

                return {
                    "limit": core_rate.limit,
                    "remaining": core_rate.remaining,
                    "reset": core_rate.reset,
                    "used": core_rate.limit - core_rate.remaining,
                }

            result = await self._run_sync(_get_rate_limit)
            logger.debug(
                f"Rate limit: {result['remaining']}/{result['limit']} "
                f"(resets at {result['reset']})"
            )
            return result

        except GithubException as e:
            self._handle_github_exception(e)
            raise  # For type checker
        except Exception as e:
            logger.error(f"Unexpected error getting rate limit: {e}")
            raise GitHubAPIError(f"Failed to get rate limit: {e}")

    async def close(self) -> None:
        """
        Close the GitHub client and cleanup resources.

        Should be called when done with the client.
        """
        if self._client:
            # PyGithub doesn't have explicit close, but we shutdown executor
            self._executor.shutdown(wait=False)
            self._client = None
            logger.debug("GitHub client closed")
