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
    
    def _make_request(self, method, endpoint, params=None, json_data=None):
        """Make HTTP request to Asana API."""
        url = f"{self.BASE_URL}{endpoint}"
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=self.headers, params=params, timeout=10)
            elif method == 'POST':
                response = requests.post(url, headers=self.headers, json=json_data, params=params, timeout=10)
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
            # First, get current user
            user_response = self._make_request('GET', '/users/me')
            user_id = user_response['data']['gid']
            
            # Get incomplete tasks assigned to user
            params = {
                'assignee': user_id,
                'completed_since': 'now',
                'opt_fields': 'gid,name,due_on,completed,projects.name,custom_fields'
            }
            
            response = self._make_request('GET', '/tasks', params=params)
            return response.get('data', [])
        
        except Exception as e:
            logger.error(f"Error getting my tasks: {str(e)}")
            return []
    
    def get_task_details(self, task_id):
        """Get full task details including comments and subtasks."""
        try:
            params = {
                'opt_fields': 'gid,name,description,due_on,completed,assignee.name,projects.name,custom_fields,attachments.url,attachments.name,subtasks'
            }
            
            response = self._make_request('GET', f'/tasks/{task_id}', params=params)
            return response.get('data', {})
        
        except Exception as e:
            logger.error(f"Error getting task details for {task_id}: {str(e)}")
            return {}
    
    def get_task_attachments(self, task_id):
        """Get attachments for a task."""
        try:
            params = {
                'opt_fields': 'gid,name,resource_type,created_at,url'
            }
            
            response = self._make_request('GET', f'/tasks/{task_id}/attachments', params=params)
            return response.get('data', [])
        
        except Exception as e:
            logger.error(f"Error getting attachments for {task_id}: {str(e)}")
            return []
    
    def get_recent_tasks(self, days=7):
        """Get recently created or modified tasks."""
        try:
            # Calculate date range
            end_date = datetime.utcnow().isoformat() + 'Z'
            start_date = (datetime.utcnow() - timedelta(days=days)).isoformat() + 'Z'
            
            params = {
                'opt_fields': 'gid,name,due_on,completed,projects.name,created_at,modified_at',
                'limit': 50
            }
            
            # Get user's workspace
            user_response = self._make_request('GET', '/users/me')
            workspace_id = user_response['data']['workspaces'][0]['gid']
            
            # Fetch tasks from workspace
            response = self._make_request(
                'GET',
                f'/workspaces/{workspace_id}/tasks/search',
                params={
                    **params,
                    'modified_after': start_date,
                    'modified_before': end_date
                }
            )
            
            return response.get('data', [])
        
        except Exception as e:
            logger.error(f"Error getting recent tasks: {str(e)}")
            return []
    
    def search_tasks(self, query):
        """Search tasks by text query."""
        try:
            # Get user's workspace
            user_response = self._make_request('GET', '/users/me')
            workspace_id = user_response['data']['workspaces'][0]['gid']
            
            params = {
                'opt_fields': 'gid,name,due_on,completed,projects.name',
                'text': query,
                'limit': 20
            }
            
            response = self._make_request(
                'GET',
                f'/workspaces/{workspace_id}/tasks/search',
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
