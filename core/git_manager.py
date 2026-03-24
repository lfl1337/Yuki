"""
Git automation — wraps gitpython for auto commit/push.
"""

import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

try:
    import git as gitpython
    _GIT_AVAILABLE = True
except ImportError:
    _GIT_AVAILABLE = False
    logger.warning("gitpython not installed — git features disabled")


class GitManager:
    """Manages a local git repository with auto commit/push support."""

    def __init__(self, repo_path: str, remote_url: str = ""):
        self._repo_path = Path(repo_path)
        self._remote_url = remote_url
        self._repo = None

        if not _GIT_AVAILABLE:
            return

        try:
            if (self._repo_path / ".git").exists():
                self._repo = gitpython.Repo(str(self._repo_path))
            else:
                self._repo = gitpython.Repo.init(str(self._repo_path))
            if remote_url:
                self._ensure_remote(remote_url)
        except Exception as exc:
            logger.error("GitManager init failed: %s", exc)

    def _ensure_remote(self, url: str):
        if self._repo is None:
            return
        try:
            origin = self._repo.remotes.origin
            if origin.url != url:
                origin.set_url(url)
        except AttributeError:
            self._repo.create_remote("origin", url)

    def is_available(self) -> bool:
        return _GIT_AVAILABLE and self._repo is not None

    def status(self) -> dict:
        if not self.is_available():
            return {"staged": [], "unstaged": [], "untracked": [], "branch": "unknown", "has_changes": False}
        try:
            repo = self._repo
            staged = [item.a_path for item in repo.index.diff("HEAD")]
            unstaged = [item.a_path for item in repo.index.diff(None)]
            untracked = repo.untracked_files
            branch = repo.active_branch.name
            has_changes = bool(staged or unstaged or untracked)
            return {
                "staged": staged,
                "unstaged": unstaged,
                "untracked": untracked,
                "branch": branch,
                "has_changes": has_changes,
            }
        except Exception as exc:
            logger.error("git status failed: %s", exc)
            return {"staged": [], "unstaged": [], "untracked": [], "branch": "unknown", "has_changes": False}

    def get_current_branch(self) -> str:
        if not self.is_available():
            return "unknown"
        try:
            return self._repo.active_branch.name
        except Exception:
            return "unknown"

    def add_all(self):
        if not self.is_available():
            return
        try:
            self._repo.git.add(A=True)
        except Exception as exc:
            logger.error("git add failed: %s", exc)
            raise

    def commit(self, message: str):
        if not self.is_available():
            return
        try:
            from core.version_manager import get_current_version
            version = get_current_version()
            full_message = f"[v{version}] {message}"
            self._repo.index.commit(full_message)
        except Exception as exc:
            logger.error("git commit failed: %s", exc)
            raise

    def push(self) -> tuple:
        if not self.is_available():
            return (False, "gitpython not available")
        try:
            origin = self._repo.remotes.origin
            origin.push()
            return (True, "")
        except Exception as exc:
            logger.error("git push failed: %s", exc)
            return (False, str(exc))

    def auto_commit_push(self, message: str) -> tuple:
        try:
            self.add_all()
            self.commit(message)
            return self.push()
        except Exception as exc:
            return (False, str(exc))

    def get_log(self, n: int = 10) -> list:
        if not self.is_available():
            return []
        try:
            commits = []
            for commit in self._repo.iter_commits(max_count=n):
                commits.append({
                    "hash": commit.hexsha[:7],
                    "message": commit.message.strip(),
                    "date": commit.committed_datetime.strftime("%Y-%m-%d %H:%M"),
                    "author": str(commit.author),
                })
            return commits
        except Exception as exc:
            logger.error("git log failed: %s", exc)
            return []

    def create_tag(self, tag_name: str, message: str):
        if not self.is_available():
            return
        try:
            self._repo.create_tag(tag_name, message=message)
            self._repo.remotes.origin.push(tag_name)
        except Exception as exc:
            logger.error("git tag failed: %s", exc)
