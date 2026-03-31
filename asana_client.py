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
        self._user_name = None
        self._workspace_gid = None
        self._workspace_users = None

    def _ensure_user_info(self):
        """Cache user and workspace GIDs to avoid repeated API calls."""
        if not self._user_gid:
            response = self._make_request('GET', '/users/me')
            self._user_gid = response['data']['gid']
            self._user_name = response['data']['name']
            self._workspace_gid = response['data']['workspaces'][0]['gid']

    def _make_request(self, method, endpoint, params=None, json_data=None):
        """Make HTTP request to Asana API."""
        url = f"{self.BASE_URL}{endpoint}"

        try:
            if method == 'GET':
                response = requests.get(url, headers=self.headers, params=params, timeout=15)
            elif method == 'POST':
                response = requests.post(url, headers=self.headers, json=json_data, params=params, timeout=15)
            elif method == 'PUT':
                response = requests.put(url, headers=self.headers, json=json_data, params=params, timeout=15)
            else:
                raise ValueError(f"Unsupported method: {method}")

            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            logger.error(f"Asana API request failed: {method} {endpoint} - {str(e)}")
            raise

    # ─── READ OPERATIONS ───

    def get_my_tasks(self):
        """Get incomplete tasks assigned to the current user."""
        try:
            self._ensure_user_info()

            # Step 1: Get the user's task list GID
            task_list_response = self._make_request(
                'GET',
                f'/users/{self._user_gid}/user_task_list',
                params={'workspace': self._workspace_gid}
            )
            task_list_gid = task_list_response['data']['gid']

            # Step 2: Get incomplete tasks from that task list
            params = {
                'completed_since': 'now',
                'opt_fields': 'gid,name,due_on,projects.name,assignee.name,custom_fields.name,custom_fields.display_value',
                'limit': 100
            }
            response = self._make_request('GET', f'/user_task_lists/{task_list_gid}/tasks', params=params)
            return response.get('data', [])

        except Exception as e:
            logger.error(f"Error getting my tasks: {str(e)}")
            return []

    def get_task_details(self, task_id):
        """Get full task details including notes, assignee, and projects."""
        try:
            params = {
                'opt_fields': 'gid,name,notes,due_on,completed,assignee.name,assignee.gid,projects.name,followers.name,custom_fields.name,custom_fields.display_value'
            }
            response = self._make_request('GET', f'/tasks/{task_id}', params=params)
            return response.get('data', {})

        except Exception as e:
            logger.error(f"Error getting task details for {task_id}: {str(e)}")
            return {}

    def get_task_stories(self, task_id, limit=20):
        """Get comments/stories on a task (includes comments and system events)."""
        try:
            params = {
                'opt_fields': 'gid,created_at,created_by.name,text,type,resource_subtype',
                'limit': limit
            }
            response = self._make_request('GET', f'/tasks/{task_id}/stories', params=params)
            stories = response.get('data', [])
            # Filter to just comments (not system events)
            comments = [s for s in stories if s.get('resource_subtype') == 'comment_added']
            return comments

        except Exception as e:
            logger.error(f"Error getting stories for task {task_id}: {str(e)}")
            return []

    def get_task_attachments(self, task_id):
        """Get attachments for a task."""
        try:
            response = self._make_request('GET', f'/tasks/{task_id}/attachments')
            return response.get('data', [])

        except Exception as e:
            logger.error(f"Error getting attachments for {task_id}: {str(e)}")
            return []

    def get_recent_tasks(self, days=7):
        """Get recently modified tasks assigned to the user."""
        try:
            self._ensure_user_info()
            start_date = (datetime.utcnow() - timedelta(days=days)).strftime('%Y-%m-%d')

            params = {
                'opt_fields': 'gid,name,due_on,projects.name,modified_at,assignee.name',
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

    def get_tasks_with_recent_comments(self, days=2):
        """Get tasks where the user was recently mentioned in comments."""
        try:
            self._ensure_user_info()
            start_date = (datetime.utcnow() - timedelta(days=days)).strftime('%Y-%m-%d')

            # Search for tasks commented on recently in the workspace
            params = {
                'opt_fields': 'gid,name,due_on,projects.name,modified_at',
                'commented_on_by.any': self._user_gid,
                'modified_on.after': start_date,
                'is_subtask': 'false',
                'sort_by': 'modified_at',
                'sort_ascending': 'false',
                'limit': 10
            }

            response = self._make_request(
                'GET',
                f'/workspaces/{self._workspace_gid}/tasks/search',
                params=params
            )
            return response.get('data', [])

        except Exception as e:
            logger.error(f"Error getting tasks with recent comments: {str(e)}")
            return []

    def get_new_tasks_assigned(self, days=1):
        """Get newly created tasks assigned to the user (tasks they may have missed)."""
        try:
            self._ensure_user_info()
            start_date = (datetime.utcnow() - timedelta(days=days)).strftime('%Y-%m-%d')

            params = {
                'opt_fields': 'gid,name,due_on,projects.name,created_at,assignee.name',
                'assignee.any': self._user_gid,
                'created_on.after': start_date,
                'is_subtask': 'false',
                'sort_by': 'created_at',
                'sort_ascending': 'false',
                'limit': 15
            }

            response = self._make_request(
                'GET',
                f'/workspaces/{self._workspace_gid}/tasks/search',
                params=params
            )
            return response.get('data', [])

        except Exception as e:
            logger.error(f"Error getting new tasks: {str(e)}")
            return []

    def search_tasks(self, query):
        """Search tasks by text query."""
        try:
            self._ensure_user_info()

            params = {
                'opt_fields': 'gid,name,due_on,projects.name,assignee.name',
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

    # ─── WRITE OPERATIONS ───

    def update_task(self, task_id, updates):
        """
        Update a task's fields.

        updates can include:
            name (str), notes (str), due_on (str YYYY-MM-DD),
            completed (bool), assignee (str user GID)
        """
        try:
            json_data = {'data': updates}
            response = self._make_request('PUT', f'/tasks/{task_id}', json_data=json_data)
            return response.get('data', {})

        except Exception as e:
            logger.error(f"Error updating task {task_id}: {str(e)}")
            return {}

    def complete_task(self, task_id):
        """Mark a task as complete."""
        return self.update_task(task_id, {'completed': True})

    def add_comment(self, task_id, text):
        """Add a comment to a task (posted as the PAT owner = Fredy)."""
        try:
            json_data = {'data': {'text': text}}
            response = self._make_request('POST', f'/tasks/{task_id}/stories', json_data=json_data)
            return response.get('data', {})

        except Exception as e:
            logger.error(f"Error adding comment to task {task_id}: {str(e)}")
            return {}

    def assign_task(self, task_id, assignee_gid):
        """Assign a task to a specific user by their GID."""
        return self.update_task(task_id, {'assignee': assignee_gid})

    def set_due_date(self, task_id, due_date):
        """Set or update a task's due date (YYYY-MM-DD format)."""
        return self.update_task(task_id, {'due_on': due_date})

    # ─── USER LOOKUP ───

    def get_workspace_users(self):
        """Get all users in the workspace (cached)."""
        if self._workspace_users is not None:
            return self._workspace_users

        try:
            self._ensure_user_info()
            params = {
                'opt_fields': 'gid,name,email',
                'limit': 100
            }
            response = self._make_request(
                'GET',
                f'/workspaces/{self._workspace_gid}/users',
                params=params
            )
            self._workspace_users = response.get('data', [])
            return self._workspace_users

        except Exception as e:
            logger.error(f"Error getting workspace users: {str(e)}")
            return []

    def find_user_by_name(self, name_query):
        """Find a user by partial name match. Returns first match or None."""
        users = self.get_workspace_users()
        name_query_lower = name_query.lower()
        for user in users:
            if name_query_lower in user.get('name', '').lower():
                return user
        return None

    # ─── PROJECT OPERATIONS ───

    def get_projects(self):
        """Get all projects in the workspace."""
        try:
            self._ensure_user_info()
            params = {
                'workspace': self._workspace_gid,
                'opt_fields': 'gid,name,owner.name,due_on,current_status_update.title',
                'limit': 50
            }
            response = self._make_request('GET', '/projects', params=params)
            return response.get('data', [])

        except Exception as e:
            logger.error(f"Error getting projects: {str(e)}")
            return []

    def get_project_tasks(self, project_id, only_incomplete=True):
        """Get tasks from a specific project."""
        try:
            params = {
                'opt_fields': 'gid,name,due_on,assignee.name,completed',
                'limit': 50
            }
            if only_incomplete:
                params['completed_since'] = 'now'

            response = self._make_request('GET', f'/projects/{project_id}/tasks', params=params)
            return response.get('data', [])

        except Exception as e:
            logger.error(f"Error getting project tasks for {project_id}: {str(e)}")
            return []
