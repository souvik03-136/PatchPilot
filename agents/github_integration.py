from github import Github, GithubException
import base64
import re
import os
from typing import Dict, List, Optional, Tuple
import difflib
from datetime import datetime
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GitHubIntegration:
    def __init__(self, token: str = None):
        # Load token from environment if not provided
        if token is None:
            token = os.getenv('GITHUB_TOKEN') or os.getenv('GH_TOKEN')
            if not token:
                raise ValueError("GitHub token not found. Please set GITHUB_TOKEN or GH_TOKEN environment variable, or pass token directly.")
        
        self.token = token
        self.client = Github(token)
        self.rate_limit_remaining = None
        self.rate_limit_reset = None
        self._update_rate_limit_info()

    def _update_rate_limit_info(self):
        """Update rate limit information"""
        try:
            rate_limit = self.client.get_rate_limit()
            self.rate_limit_remaining = rate_limit.core.remaining
            self.rate_limit_reset = rate_limit.core.reset
            logger.info(f"Rate limit remaining: {self.rate_limit_remaining}")
        except GithubException as e:
            logger.warning(f"Could not get rate limit info: {e}")

    def get_pr_details(self, repo_name: str, pr_id: int) -> Optional[Dict]:
        """Get comprehensive PR details including files, commits, and metadata"""
        try:
            print(f"GitHub API Rate Limit: {self.rate_limit_remaining}/{self.rate_limit_reset}")
            repo = self.client.get_repo(repo_name)
            pr = repo.get_pull(pr_id)
            
            # Get PR files
            files = []
            for file in pr.get_files():
                file_info = {
                    'filename': file.filename,
                    'status': file.status,  # added, modified, removed, renamed
                    'additions': file.additions,
                    'deletions': file.deletions,
                    'changes': file.changes,
                    'patch': file.patch if hasattr(file, 'patch') else None,
                    'blob_url': file.blob_url,
                    'raw_url': file.raw_url,
                    'contents_url': file.contents_url
                }
                files.append(file_info)
            
            # Get commits
            commits = []
            for commit in pr.get_commits():
                commit_info = {
                    'sha': commit.sha,
                    'message': commit.commit.message,
                    'author': commit.commit.author.name,
                    'date': commit.commit.author.date,
                    'url': commit.html_url
                }
                commits.append(commit_info)
            
            # Get reviews
            reviews = []
            for review in pr.get_reviews():
                review_info = {
                    'id': review.id,
                    'user': review.user.login,
                    'state': review.state,
                    'body': review.body,
                    'submitted_at': review.submitted_at
                }
                reviews.append(review_info)
            
            pr_details = {
                'id': pr.id,
                'number': pr.number,
                'title': pr.title,
                'body': pr.body,
                'state': pr.state,
                'created_at': pr.created_at,
                'updated_at': pr.updated_at,
                'closed_at': pr.closed_at,
                'merged_at': pr.merged_at,
                'merge_commit_sha': pr.merge_commit_sha,
                'author': pr.user.login,
                'assignees': [assignee.login for assignee in pr.assignees],
                'reviewers': [reviewer.login for reviewer in pr.requested_reviewers],
                'labels': [label.name for label in pr.labels],
                'milestone': pr.milestone.title if pr.milestone else None,
                'base_branch': pr.base.ref,
                'head_branch': pr.head.ref,
                'base_sha': pr.base.sha,
                'head_sha': pr.head.sha,
                'mergeable': pr.mergeable,
                'mergeable_state': pr.mergeable_state,
                'merged': pr.merged,
                'comments': pr.comments,
                'review_comments': pr.review_comments,
                'commits': pr.commits,
                'additions': pr.additions,
                'deletions': pr.deletions,
                'changed_files': pr.changed_files,
                'files': files,
                'commits_data': commits,
                'reviews': reviews,
                'html_url': pr.html_url,
                'diff_url': pr.diff_url,
                'patch_url': pr.patch_url
            }
            
            return pr_details
            
        except GithubException as e:
            logger.error(f"Error getting PR details: {e}")
            return None

    def get_file_content(self, repo_name: str, file_path: str, ref: str = None) -> Optional[str]:
        """Get file content from repository with proper 404 handling"""
        try:
            repo = self.client.get_repo(repo_name)
            try:
                file = repo.get_contents(file_path, ref=ref)
                return file.decoded_content.decode('utf-8')
            except GithubException as e:
                if e.status == 404:
                    logger.warning(f"File not found: {file_path}@{ref if ref else 'default'}")
                    return None
                else:
                    logger.error(f"Error getting file content for {file_path}: {e}")
                    return None
        except GithubException as e:
            logger.error(f"Error accessing repository {repo_name}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error getting file content: {e}")
            return None

    def get_file_history(self, repo_name: str, file_path: str, limit: int = 10) -> List[Dict]:
        """Get commit history for a specific file"""
        try:
            repo = self.client.get_repo(repo_name)
            commits = repo.get_commits(path=file_path)
            
            history = []
            for i, commit in enumerate(commits):
                if i >= limit:
                    break
                    
                commit_info = {
                    'sha': commit.sha,
                    'message': commit.commit.message,
                    'author': commit.commit.author.name,
                    'date': commit.commit.author.date,
                    'url': commit.html_url
                }
                history.append(commit_info)
            
            return history
            
        except GithubException as e:
            logger.error(f"Error getting file history: {e}")
            return []

    def analyze_pr_changes(self, repo_name: str, pr_id: int) -> Dict:
        """Analyze PR changes and provide insights"""
        pr_details = self.get_pr_details(repo_name, pr_id)
        if not pr_details:
            return {}
        
        analysis = {
            'summary': {
                'total_files': pr_details['changed_files'],
                'total_additions': pr_details['additions'],
                'total_deletions': pr_details['deletions'],
                'total_commits': pr_details['commits']
            },
            'files_by_type': {},
            'large_files': [],
            'potential_issues': [],
            'complexity_score': 0
        }
        
        # Analyze files
        for file_info in pr_details['files']:
            # Group by file extension
            ext = file_info['filename'].split('.')[-1] if '.' in file_info['filename'] else 'no_extension'
            if ext not in analysis['files_by_type']:
                analysis['files_by_type'][ext] = {'count': 0, 'additions': 0, 'deletions': 0}
            
            analysis['files_by_type'][ext]['count'] += 1
            analysis['files_by_type'][ext]['additions'] += file_info['additions']
            analysis['files_by_type'][ext]['deletions'] += file_info['deletions']
            
            # Identify large files (>500 lines changed)
            if file_info['changes'] > 500:
                analysis['large_files'].append({
                    'filename': file_info['filename'],
                    'changes': file_info['changes']
                })
            
            # Check for potential issues
            if file_info['status'] == 'removed':
                analysis['potential_issues'].append(f"File deleted: {file_info['filename']}")
            
            if file_info['filename'].endswith('.py') and file_info['changes'] > 200:
                analysis['potential_issues'].append(f"Large Python file change: {file_info['filename']}")
        
        # Calculate complexity score
        complexity_score = 0
        complexity_score += pr_details['changed_files'] * 2
        complexity_score += pr_details['additions'] * 0.1
        complexity_score += pr_details['deletions'] * 0.1
        complexity_score += len(analysis['large_files']) * 10
        
        analysis['complexity_score'] = round(complexity_score, 2)
        
        return analysis

    def get_pr_diff(self, repo_name: str, pr_id: int) -> Optional[str]:
        """Get full diff for PR"""
        try:
            repo = self.client.get_repo(repo_name)
            pr = repo.get_pull(pr_id)
            
            # Get diff via API
            diff_url = pr.diff_url
            import requests
            response = requests.get(diff_url, headers={'Authorization': f'token {self.token}'})
            
            if response.status_code == 200:
                return response.text
            else:
                logger.error(f"Failed to get diff: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting PR diff: {e}")
            return None

    def post_comment(self, repo_name: str, pr_id: int, comment: str) -> bool:
        """Post a review comment to a GitHub Pull Request"""
        try:
            repo = self.client.get_repo(repo_name)
            pr = repo.get_pull(pr_id)
            pr.create_issue_comment(comment)
            logger.info(f"Posted comment to PR #{pr_id}")
            return True
        except GithubException as e:
            logger.error(f"Error posting comment: {e}")
            return False

    def post_line_comment(self, repo_name: str, pr_id: int, filename: str, line: int, comment: str) -> bool:
        """Post a comment on a specific line in a PR"""
        try:
            repo = self.client.get_repo(repo_name)
            pr = repo.get_pull(pr_id)
            
            # Create a review comment on specific line
            pr.create_review_comment(
                body=comment,
                commit=pr.head.sha,
                path=filename,
                line=line
            )
            logger.info(f"Posted line comment to {filename}:{line}")
            return True
        except GithubException as e:
            logger.error(f"Error posting line comment: {e}")
            return False

    def create_branch(self, repo_name: str, base: str, branch: str) -> bool:
        """Create a new branch from base"""
        try:
            repo = self.client.get_repo(repo_name)
            source = repo.get_branch(base)
            repo.create_git_ref(ref=f"refs/heads/{branch}", sha=source.commit.sha)
            logger.info(f"Created branch {branch} from {base}")
            return True
        except GithubException as e:
            logger.error(f"Error creating branch: {e}")
            return False

    def commit_patches(self, repo_name: str, branch: str, patches: List[Dict]) -> bool:
        """Commit patches to the branch"""
        try:
            repo = self.client.get_repo(repo_name)
            
            for patch in patches:
                file_path = patch["file"]
                patch_content = patch.get("patch", "")
                message = patch.get("fix_description", f"Apply patch to {file_path}")
                
                try:
                    # Get current file content
                    file = repo.get_contents(file_path, ref=branch)
                    current_content = file.decoded_content.decode('utf-8')
                    
                    # Apply patch
                    if patch_content:
                        updated_content = self._apply_patch(current_content, patch_content)
                    else:
                        updated_content = patch.get("content", current_content)
                    
                    # Update file
                    repo.update_file(
                        path=file_path,
                        message=message,
                        content=updated_content,
                        sha=file.sha,
                        branch=branch
                    )
                    logger.info(f"Applied patch to {file_path}")
                    
                except GithubException as e:
                    if e.status == 404:
                        # File doesn't exist, create it
                        repo.create_file(
                            path=file_path,
                            message=message,
                            content=patch.get("content", ""),
                            branch=branch
                        )
                        logger.info(f"Created new file {file_path}")
                    else:
                        logger.error(f"Error updating {file_path}: {e}")
                        return False
            
            return True
            
        except GithubException as e:
            logger.error(f"Error committing patches: {e}")
            return False

    def create_pr(self, repo_name: str, base: str, branch: str, title: str, body: str) -> Optional[int]:
        """Create a Pull Request with the patch branch"""
        try:
            repo = self.client.get_repo(repo_name)
            pr = repo.create_pull(title=title, body=body, base=base, head=branch)
            logger.info(f"Created PR #{pr.number}: {title}")
            return pr.number
        except GithubException as e:
            logger.error(f"Error creating PR: {e}")
            return None

    def block_merge(self, repo_name: str, pr_id: int, reason: str) -> bool:
        """Post a blocking review on PR"""
        try:
            repo = self.client.get_repo(repo_name)
            pr = repo.get_pull(pr_id)
            pr.create_review(
                body=reason,
                event="REQUEST_CHANGES"
            )
            logger.info(f"Blocked merge for PR #{pr_id}")
            return True
        except GithubException as e:
            logger.error(f"Error blocking merge: {e}")
            return False

    def approve_pr(self, repo_name: str, pr_id: int, comment: str = "") -> bool:
        """Approve a PR"""
        try:
            repo = self.client.get_repo(repo_name)
            pr = repo.get_pull(pr_id)
            pr.create_review(
                body=comment,
                event="APPROVE"
            )
            logger.info(f"Approved PR #{pr_id}")
            return True
        except GithubException as e:
            logger.error(f"Error approving PR: {e}")
            return False

    def merge_pr(self, repo_name: str, pr_id: int, merge_method: str = "merge") -> bool:
        """Merge a PR"""
        try:
            repo = self.client.get_repo(repo_name)
            pr = repo.get_pull(pr_id)
            
            if merge_method == "squash":
                pr.merge(merge_method="squash")
            elif merge_method == "rebase":
                pr.merge(merge_method="rebase")
            else:
                pr.merge(merge_method="merge")
            
            logger.info(f"Merged PR #{pr_id} using {merge_method}")
            return True
        except GithubException as e:
            logger.error(f"Error merging PR: {e}")
            return False

    def close_pr(self, repo_name: str, pr_id: int) -> bool:
        """Close a PR without merging"""
        try:
            repo = self.client.get_repo(repo_name)
            pr = repo.get_pull(pr_id)
            pr.edit(state="closed")
            logger.info(f"Closed PR #{pr_id}")
            return True
        except GithubException as e:
            logger.error(f"Error closing PR: {e}")
            return False

    def get_pr_comments(self, repo_name: str, pr_id: int) -> List[Dict]:
        """Get all comments on a PR"""
        try:
            repo = self.client.get_repo(repo_name)
            pr = repo.get_pull(pr_id)
            
            comments = []
            
            # Get issue comments
            for comment in pr.get_issue_comments():
                comment_data = {
                    'id': comment.id,
                    'type': 'issue_comment',
                    'author': comment.user.login,
                    'body': comment.body,
                    'created_at': comment.created_at,
                    'updated_at': comment.updated_at
                }
                comments.append(comment_data)
            
            # Get review comments
            for comment in pr.get_review_comments():
                comment_data = {
                    'id': comment.id,
                    'type': 'review_comment',
                    'author': comment.user.login,
                    'body': comment.body,
                    'path': comment.path,
                    'line': comment.line,
                    'created_at': comment.created_at,
                    'updated_at': comment.updated_at
                }
                comments.append(comment_data)
            
            return sorted(comments, key=lambda x: x['created_at'])
            
        except GithubException as e:
            logger.error(f"Error getting PR comments: {e}")
            return []

    def search_code(self, repo_name: str, query: str, file_extension: str = None) -> List[Dict]:
        """Search for code in repository"""
        try:
            search_query = f"repo:{repo_name} {query}"
            if file_extension:
                search_query += f" extension:{file_extension}"
            
            results = self.client.search_code(search_query)
            
            search_results = []
            for result in results:
                result_data = {
                    'name': result.name,
                    'path': result.path,
                    'sha': result.sha,
                    'url': result.html_url,
                    'repository': result.repository.full_name,
                    'score': result.score
                }
                search_results.append(result_data)
            
            return search_results
            
        except GithubException as e:
            logger.error(f"Error searching code: {e}")
            return []

    def get_repository_info(self, repo_name: str) -> Optional[Dict]:
        """Get comprehensive repository information"""
        try:
            repo = self.client.get_repo(repo_name)
            
            repo_info = {
                'name': repo.name,
                'full_name': repo.full_name,
                'description': repo.description,
                'private': repo.private,
                'fork': repo.fork,
                'created_at': repo.created_at,
                'updated_at': repo.updated_at,
                'pushed_at': repo.pushed_at,
                'size': repo.size,
                'language': repo.language,
                'languages': repo.get_languages(),
                'forks_count': repo.forks_count,
                'stargazers_count': repo.stargazers_count,
                'watchers_count': repo.watchers_count,
                'open_issues_count': repo.open_issues_count,
                'default_branch': repo.default_branch,
                'topics': repo.get_topics(),
                'license': repo.license.name if repo.license else None,
                'clone_url': repo.clone_url,
                'ssh_url': repo.ssh_url,
                'html_url': repo.html_url
            }
            
            return repo_info
            
        except GithubException as e:
            logger.error(f"Error getting repository info: {e}")
            return None

    def _apply_patch(self, original_content: str, patch: str) -> str:
        """
        Apply a unified diff patch to content
        """
        if not patch:
            return original_content
        
        try:
            # Parse the patch
            lines = patch.split('\n')
            original_lines = original_content.split('\n')
            
            # Simple patch application - this is a basic implementation
            # For production use, consider using a proper diff library
            
            result_lines = []
            i = 0
            patch_line = 0
            
            while patch_line < len(lines):
                line = lines[patch_line]
                
                if line.startswith('@@'):
                    # Parse hunk header
                    match = re.match(r'@@ -(\d+),?(\d*) \+(\d+),?(\d*) @@', line)
                    if match:
                        old_start = int(match.group(1)) - 1  # Convert to 0-based
                        new_start = int(match.group(3)) - 1  # Convert to 0-based
                        
                        # Copy lines before the hunk
                        while i < old_start:
                            if i < len(original_lines):
                                result_lines.append(original_lines[i])
                            i += 1
                
                elif line.startswith('-'):
                    # Line to be removed - skip it
                    i += 1
                    
                elif line.startswith('+'):
                    # Line to be added
                    result_lines.append(line[1:])
                    
                elif line.startswith(' '):
                    # Context line - keep it
                    if i < len(original_lines):
                        result_lines.append(original_lines[i])
                        i += 1
                
                patch_line += 1
            
            # Add remaining lines
            while i < len(original_lines):
                result_lines.append(original_lines[i])
                i += 1
            
            return '\n'.join(result_lines)
            
        except Exception as e:
            logger.error(f"Error applying patch: {e}")
            return original_content

    def create_issue(self, repo_name: str, title: str, body: str, labels: List[str] = None, assignees: List[str] = None) -> Optional[int]:
        """Create a new issue"""
        try:
            repo = self.client.get_repo(repo_name)
            
            issue = repo.create_issue(
                title=title,
                body=body,
                labels=labels or [],
                assignees=assignees or []
            )
            
            logger.info(f"Created issue #{issue.number}: {title}")
            return issue.number
            
        except GithubException as e:
            logger.error(f"Error creating issue: {e}")
            return None

    def get_workflows(self, repo_name: str) -> List[Dict]:
        """Get GitHub Actions workflows"""
        try:
            repo = self.client.get_repo(repo_name)
            workflows = repo.get_workflows()
            
            workflow_list = []
            for workflow in workflows:
                workflow_data = {
                    'id': workflow.id,
                    'name': workflow.name,
                    'path': workflow.path,
                    'state': workflow.state,
                    'created_at': workflow.created_at,
                    'updated_at': workflow.updated_at,
                    'url': workflow.html_url
                }
                workflow_list.append(workflow_data)
            
            return workflow_list
            
        except GithubException as e:
            logger.error(f"Error getting workflows: {e}")
            return []

    def get_workflow_runs(self, repo_name: str, workflow_id: int = None) -> List[Dict]:
        """Get workflow runs"""
        try:
            repo = self.client.get_repo(repo_name)
            
            if workflow_id:
                workflow = repo.get_workflow(workflow_id)
                runs = workflow.get_runs()
            else:
                runs = repo.get_workflow_runs()
            
            run_list = []
            for run in runs:
                run_data = {
                    'id': run.id,
                    'name': run.name,
                    'status': run.status,
                    'conclusion': run.conclusion,
                    'workflow_id': run.workflow_id,
                    'head_branch': run.head_branch,
                    'head_sha': run.head_sha,
                    'created_at': run.created_at,
                    'updated_at': run.updated_at,
                    'url': run.html_url
                }
                run_list.append(run_data)
            
            return run_list
            
        except GithubException as e:
            logger.error(f"Error getting workflow runs: {e}")
            return []

'''
# Usage Example
if __name__ == "__main__":
    # Initialize with token from environment (GITHUB_TOKEN or GH_TOKEN)
    # Or pass token directly: GitHubIntegration("your_token_here")
    gh = GitHubIntegration()
    
    # Example: Analyze a PR
    repo_name = "owner/repository"
    pr_id = 123
    
    # Get PR details
    pr_details = gh.get_pr_details(repo_name, pr_id)
    if pr_details:
        print(f"PR #{pr_details['number']}: {pr_details['title']}")
        print(f"Files changed: {pr_details['changed_files']}")
        print(f"Additions: {pr_details['additions']}, Deletions: {pr_details['deletions']}")
    
    # Analyze changes
    analysis = gh.analyze_pr_changes(repo_name, pr_id)
    print(f"Complexity score: {analysis['complexity_score']}")
    
    # Post a comment
    gh.post_comment(repo_name, pr_id, "Automated analysis complete!")
    
    # Create a review branch with fixes
    fix_branch = f"automated-fixes-{pr_id}"
    gh.create_branch(repo_name, "main", fix_branch)
    
    # Apply patches
    patches = [
        {
            "file": "src/example.py",
            "content": "# Fixed code here",
            "fix_description": "Fixed linting issues"
        }
    ]
    gh.commit_patches(repo_name, fix_branch, patches)
    
    # Create PR with fixes
    fix_pr = gh.create_pr(
        repo_name,
        "main",
        fix_branch,
        f"Automated fixes for PR #{pr_id}",
        "This PR contains automated fixes for the issues found in the original PR."
    )'''