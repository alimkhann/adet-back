import os
import logging
from typing import Optional, Dict, Any
from datetime import datetime

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("Requests library not available. GitHub integration disabled.")

logger = logging.getLogger(__name__)


class GitHubService:
    def __init__(self):
        self.github_token = os.getenv("GITHUB_TOKEN")
        self.github_owner = os.getenv("GITHUB_OWNER", "alimkhann")
        self.github_repo = os.getenv("GITHUB_REPO", "adet-back")
        self.github_api_url = f"https://api.github.com/repos/{self.github_owner}/{self.github_repo}/issues"

        self.enabled = bool(self.github_token and REQUESTS_AVAILABLE)

    def create_issue_from_bug_report(self, bug_report: Dict[str, Any]) -> Optional[str]:
        """Create a GitHub issue from a bug report"""
        if not self.enabled:
            logger.warning("GitHub integration not configured. Skipping issue creation.")
            return None

        try:
            # Create issue title
            title = f"[Bug] {bug_report['title']}"

            # Create issue body
            body = self._format_bug_report_body(bug_report)

            # Create issue labels
            labels = self._get_issue_labels(bug_report)

            # Prepare issue data
            issue_data = {
                "title": title,
                "body": body,
                "labels": labels
            }

            # Create the issue
            headers = {
                "Authorization": f"token {self.github_token}",
                "Accept": "application/vnd.github.v3+json"
            }

            response = requests.post(
                self.github_api_url,
                json=issue_data,
                headers=headers
            )

            if response.status_code == 201:
                issue = response.json()
                issue_url = issue.get("html_url")
                logger.info(f"Created GitHub issue: {issue_url}")
                return issue_url
            else:
                logger.error(f"Failed to create GitHub issue: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"Error creating GitHub issue: {e}")
            return None

    def _format_bug_report_body(self, bug_report: Dict[str, Any]) -> str:
        """Format bug report data for GitHub issue body"""
        body = f"""
## Bug Report

**Report ID:** #{bug_report['id']}
**Category:** {bug_report['category']}
**Severity:** {bug_report['severity']}
**Reported by:** {bug_report.get('user_email', 'Unknown')}
**Reported at:** {bug_report['created_at']}

### Description
{bug_report['description']}

"""

        if bug_report.get('steps_to_reproduce'):
            body += f"""
### Steps to Reproduce
{bug_report['steps_to_reproduce']}

"""

        if bug_report.get('expected_behavior'):
            body += f"""
### Expected Behavior
{bug_report['expected_behavior']}

"""

        if bug_report.get('actual_behavior'):
            body += f"""
### Actual Behavior
{bug_report['actual_behavior']}

"""

        if bug_report.get('system_info'):
            body += f"""
### System Information
- App Version: {bug_report['system_info'].get('app_version', 'Unknown')}
- Build Number: {bug_report['system_info'].get('build_number', 'Unknown')}
- iOS Version: {bug_report['system_info'].get('ios_version', 'Unknown')}
- Device Model: {bug_report['system_info'].get('device_model', 'Unknown')}
- Device Name: {bug_report['system_info'].get('device_name', 'Unknown')}
- Language: {bug_report['system_info'].get('language', 'Unknown')}
- Timezone: {bug_report['system_info'].get('timezone', 'Unknown')}

"""

        body += f"""
---
*This issue was automatically created from a bug report submitted through the Adet app.*
"""

        return body.strip()

    def _get_issue_labels(self, bug_report: Dict[str, Any]) -> list:
        """Get appropriate labels for the GitHub issue"""
        labels = ["bug", "from-app"]

        # Add category label
        category = bug_report['category']
        if category in ['ui', 'performance', 'crash', 'authentication']:
            labels.append(category)

        # Add severity label
        severity = bug_report['severity']
        if severity in ['critical', 'high', 'medium', 'low']:
            labels.append(f"severity-{severity}")

        return labels

    def update_issue_status(self, issue_url: str, status: str) -> bool:
        """Update GitHub issue status"""
        if not self.enabled or not issue_url:
            return False

        try:
            # Extract issue number from URL
            issue_number = issue_url.split('/')[-1]

            # Map status to GitHub state
            state = "closed" if status in ["resolved", "closed"] else "open"

            # Update issue
            headers = {
                "Authorization": f"token {self.github_token}",
                "Accept": "application/vnd.github.v3+json"
            }

            update_data = {"state": state}

            response = requests.patch(
                f"{self.github_api_url}/{issue_number}",
                json=update_data,
                headers=headers
            )

            if response.status_code == 200:
                logger.info(f"Updated GitHub issue {issue_number} status to {state}")
                return True
            else:
                logger.error(f"Failed to update GitHub issue: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Error updating GitHub issue: {e}")
            return False


# Global GitHub service instance
github_service = GitHubService()
import logging
from typing import Optional, Dict, Any
from datetime import datetime

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("Requests library not available. GitHub integration disabled.")

logger = logging.getLogger(__name__)


class GitHubService:
    def __init__(self):
        self.github_token = os.getenv("GITHUB_TOKEN")
        self.github_owner = os.getenv("GITHUB_OWNER", "adet-app")
        self.github_repo = os.getenv("GITHUB_REPO", "adet-app")
        self.github_api_url = f"https://api.github.com/repos/{self.github_owner}/{self.github_repo}/issues"

        self.enabled = bool(self.github_token and REQUESTS_AVAILABLE)

    def create_issue_from_bug_report(self, bug_report: Dict[str, Any]) -> Optional[str]:
        """Create a GitHub issue from a bug report"""
        if not self.enabled:
            logger.warning("GitHub integration not configured. Skipping issue creation.")
            return None

        try:
            # Create issue title
            title = f"[Bug] {bug_report['title']}"

            # Create issue body
            body = self._format_bug_report_body(bug_report)

            # Create issue labels
            labels = self._get_issue_labels(bug_report)

            # Prepare issue data
            issue_data = {
                "title": title,
                "body": body,
                "labels": labels
            }

            # Create the issue
            headers = {
                "Authorization": f"token {self.github_token}",
                "Accept": "application/vnd.github.v3+json"
            }

            response = requests.post(
                self.github_api_url,
                json=issue_data,
                headers=headers
            )

            if response.status_code == 201:
                issue = response.json()
                issue_url = issue.get("html_url")
                logger.info(f"Created GitHub issue: {issue_url}")
                return issue_url
            else:
                logger.error(f"Failed to create GitHub issue: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"Error creating GitHub issue: {e}")
            return None

    def _format_bug_report_body(self, bug_report: Dict[str, Any]) -> str:
        """Format bug report data for GitHub issue body"""
        body = f"""
## Bug Report

**Report ID:** #{bug_report['id']}
**Category:** {bug_report['category']}
**Severity:** {bug_report['severity']}
**Reported by:** {bug_report.get('user_email', 'Unknown')}
**Reported at:** {bug_report['created_at']}

### Description
{bug_report['description']}

"""

        if bug_report.get('steps_to_reproduce'):
            body += f"""
### Steps to Reproduce
{bug_report['steps_to_reproduce']}

"""

        if bug_report.get('expected_behavior'):
            body += f"""
### Expected Behavior
{bug_report['expected_behavior']}

"""

        if bug_report.get('actual_behavior'):
            body += f"""
### Actual Behavior
{bug_report['actual_behavior']}

"""

        if bug_report.get('system_info'):
            body += f"""
### System Information
- App Version: {bug_report['system_info'].get('app_version', 'Unknown')}
- Build Number: {bug_report['system_info'].get('build_number', 'Unknown')}
- iOS Version: {bug_report['system_info'].get('ios_version', 'Unknown')}
- Device Model: {bug_report['system_info'].get('device_model', 'Unknown')}
- Device Name: {bug_report['system_info'].get('device_name', 'Unknown')}
- Language: {bug_report['system_info'].get('language', 'Unknown')}
- Timezone: {bug_report['system_info'].get('timezone', 'Unknown')}

"""

        body += f"""
---
*This issue was automatically created from a bug report submitted through the Adet app.*
"""

        return body.strip()

    def _get_issue_labels(self, bug_report: Dict[str, Any]) -> list:
        """Get appropriate labels for the GitHub issue"""
        labels = ["bug", "from-app"]

        # Add category label
        category = bug_report['category']
        if category in ['ui', 'performance', 'crash', 'authentication']:
            labels.append(category)

        # Add severity label
        severity = bug_report['severity']
        if severity in ['critical', 'high', 'medium', 'low']:
            labels.append(f"severity-{severity}")

        return labels

    def update_issue_status(self, issue_url: str, status: str) -> bool:
        """Update GitHub issue status"""
        if not self.enabled or not issue_url:
            return False

        try:
            # Extract issue number from URL
            issue_number = issue_url.split('/')[-1]

            # Map status to GitHub state
            state = "closed" if status in ["resolved", "closed"] else "open"

            # Update issue
            headers = {
                "Authorization": f"token {self.github_token}",
                "Accept": "application/vnd.github.v3+json"
            }

            update_data = {"state": state}

            response = requests.patch(
                f"{self.github_api_url}/{issue_number}",
                json=update_data,
                headers=headers
            )

            if response.status_code == 200:
                logger.info(f"Updated GitHub issue {issue_number} status to {state}")
                return True
            else:
                logger.error(f"Failed to update GitHub issue: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Error updating GitHub issue: {e}")
            return False


# Global GitHub service instance
github_service = GitHubService()

