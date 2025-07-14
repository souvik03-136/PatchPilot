from github import Github, GithubException
import base64


class GitHubIntegration:
    def __init__(self, token: str):
        self.token = token
        self.client = Github(token)

    def post_comment(self, repo_name: str, pr_id: int, comment: str) -> bool:
        """Post a review comment to a GitHub Pull Request"""
        try:
            repo = self.client.get_repo(repo_name)
            pr = repo.get_pull(pr_id)
            pr.create_issue_comment(comment)
            return True
        except GithubException as e:
            return False

    def create_branch(self, repo_name: str, base: str, branch: str) -> bool:
        """Create a new branch from base"""
        try:
            repo = self.client.get_repo(repo_name)
            source = repo.get_branch(base)
            repo.create_git_ref(ref=f"refs/heads/{branch}", sha=source.commit.sha)
            return True
        except GithubException as e:
            return False

    def commit_patches(self, repo_name: str, branch: str, patches: list) -> bool:
        """Commit patches to the branch"""
        try:
            repo = self.client.get_repo(repo_name)
            for patch in patches:
                file_path = patch["file"]
                patch_content = patch["patch"]
                file = repo.get_contents(file_path, ref=branch)
                updated_content = self._apply_patch(file.decoded_content.decode(), patch_content)
                repo.update_file(
                    path=file_path,
                    message=patch["fix_description"],
                    content=updated_content,
                    sha=file.sha,
                    branch=branch
                )
            return True
        except GithubException as e:
            return False

    def create_pr(self, repo_name: str, base: str, branch: str, title: str, body: str) -> bool:
        """Create a Pull Request with the patch branch"""
        try:
            repo = self.client.get_repo(repo_name)
            pr = repo.create_pull(title=title, body=body, base=base, head=branch)
            return True
        except GithubException as e:
            return False

    def block_merge(self, repo_name: str, pr_id: int, reason: str) -> bool:
        """Post a blocking review on PR"""
        try:
            repo = self.client.get_repo(repo_name)
            pr = repo.get_pull(pr_id)
            pr.create_review(
                body=reason,
                event="REQUEST_CHANGES"
            )
            return True
        except GithubException as e:
            return False

    def _apply_patch(self, original_content: str, patch: str) -> str:
        """
        Dummy implementation for applying a patch.
        Replace with proper diff/patch application logic.
        """
        return original_content
