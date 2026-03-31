import requests
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class AsanaClient:
    """Client for Asana REST API."""

    BASE_URL = "https://app.asana.com/api/1.0"

    def __init__(self, personal_access_token):
        self.pat = personal_access_token
        self.headers = {
            'Authorization': f'Bearer {personal_access_token}',
            'Content-Type': 'application/json'
        }
        self._user_gid = None
        self._workspace_gid = None

    def _ensure_user_info(self):
        """Cache user and workspace GIDs to avoid repeated API calls."""
        if not self._user_gid:
            response = self._make_request('GET', '/users/me')
            self._user_gid = response['data']['gid']
            self._workspace_gid = response['data']['workspaces'][0]['gid']

    def _make_request(self, method, endpoint, params=None, json_data=None):
        """Make HTTP request to Asana API."""
        url = f"{self.BASE_URL}{endpoint}"

        try:
            if method == 'GET':
                response = requests.get(url, headers=self.headers, params=params, timeout=15)
            elif method == 'POST':
                response = requests.post(url, headers=self.headers, json=json_data, params=params, timeout=15)
            else:
                raise ValueError(f"Unsupported method: {method}")

            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            logger.error(f"Asana API request failed: {str(e)}")
            raise

    def get_my_tasks(self):
        """Get incomplete tasks assigned to the current user."""
        try:
            self._ensure_user_info()

            # Step 1: Get the user's task list GID (different from user GID)
            task_list_response = self._make_request(
                'GET',
                f'/users/{self._user_gid}/user_task_list',
                params={'workspace': self._workspace_gid}
            )
            task_list_gid = task_list_response['data']['gid']

            # Step 2: Get incomplete tasks from that task list
            params = {
                'completed_since': 'now',
                'opt_fields': 'gid,name,due_on,projects.name',
                'limit': 100
            }
            response = self._make_request('GET', f'/user_task_lists/{task_list_gid}/tasks', params=params)
            return response.get('data', [])

        except Exception as e:
            logger.error(f"Error getting my tasks: {str(e)}")
            return []

    def get_task_details(self, task_id):
        """Get full task details including comments and subtasks."""
        try:
            params = {
                'opt_fields': 'gid,name,notes,due_on,completed,assignee.name,projects.name'
            }

            response = self._make_request('GET', f'/tasks/{task_id}', params=params)
            return response.get('data', {})

        except Exception as e:
            logger.error(f"Error getting task details for {task_id}: {str(e)}")
            return {}

    def get_task_attachments(self, task_id):
        """Get attachments for a task."""
        try:
            response = self._make_request('GET', f'/tasks/{task_id}/attachments')
            return response.get('data', [])

        except Exception as e:
            logger.error(f"Error getting attachments for {task_id}: {str(e)}")
            return []

    def get_recent_tasks(self, days=7):
        """Get recently created or modified tasks."""
        try:
            self._ensure_user_info()

            # Use ISO date format (date only, not datetime)
            start_date = (datetime.utcnow() - timedelta(days=days)).strftime('%Y-%m-%d')

            params = {
                'opt_fields': 'gid,name,due_on,projects.name,modified_at',
                'modified_on.after': start_date,
                'assignee.any': self._user_gid,
                'is_subtask': 'false',
                'sort_by': 'modified_at',
                'sort_ascending': 'false',
                'limit': 20
            }

            response = self._make_request(
                'GET',
                f'/workspaces/{self._workspace_gid}/tasks/search',
                params=params
            )

            return response.get('data', [])

        except Exception as e:
            logger.error(f"Error getting recent tasks: {str(e)}")
            return []

    def search_tasks(self, query):
        """Search tasks by text query."""
        try:
            self._ensure_user_info()

            params = {
                'opt_fields': 'gid,name,due_on,projects.name',
                'text': query,
                'limit': 20
            }

            response = self._make_request(
                'GET',
                f'/workspaces/{self._workspace_gid}/tasks/search',
                params=params
            )

            return response.get('data', [])

        except Exception as e:
            logger.error(f"Error searching tasks for '{query}': {str(e)}")
            return []

    def get_user_me(self):
        """Get current user information."""
        try:
            response = self._make_request('GET', '/users/me')
            return response.get('data', {})

        except Exception as e:
            logger.error(f"Error getting user info: {str(e)}")
            return {}
