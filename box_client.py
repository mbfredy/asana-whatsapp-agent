import logging
from boxsdk import CCGAuth, Client

logger = logging.getLogger(__name__)


class BoxClient:
    """Client for Box API using Client Credentials Grant (CCG) auth."""

    def __init__(self, client_id, client_secret, enterprise_id=None, user_id=None):
        """
        Initialize Box client with CCG authentication.
        Provide enterprise_id for app-level access, or user_id for user-scoped access.
        """
        try:
            if user_id:
                auth = CCGAuth(
                    client_id=client_id,
                    client_secret=client_secret,
                    user=user_id
                )
            else:
                auth = CCGAuth(
                    client_id=client_id,
                    client_secret=client_secret,
                    enterprise_id=enterprise_id
                )
            self.client = Client(auth)
            logger.info("Box client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Box client: {e}")
            self.client = None

    def search(self, query, limit=10, file_extensions=None):
        """Search for files and folders by name/content."""
        if not self.client:
            return {"error": "Box client not initialized"}
        try:
            kwargs = {'limit': limit}
            if file_extensions:
                kwargs['file_extensions'] = file_extensions
            results = self.client.search().query(query, **kwargs)
            items = []
            for item in results:
                entry = {
                    'id': item.id,
                    'name': item.name,
                    'type': item.type,
                }
                if item.type == 'file':
                    entry['size'] = getattr(item, 'size', None)
                if hasattr(item, 'parent') and item.parent:
                    entry['parent_folder'] = item.parent.get('name', '')
                items.append(entry)
                if len(items) >= limit:
                    break
            return items
        except Exception as e:
            logger.error(f"Box search error: {e}")
            return {"error": str(e)}

    def get_file_info(self, file_id):
        """Get detailed info about a file including shared link."""
        if not self.client:
            return {"error": "Box client not initialized"}
        try:
            file_obj = self.client.file(file_id).get(fields=[
                'name', 'size', 'modified_at', 'modified_by', 'created_at',
                'shared_link', 'parent', 'description', 'path_collection'
            ])
            info = {
                'id': file_obj.id,
                'name': file_obj.name,
                'size': file_obj.size,
                'modified_at': str(file_obj.modified_at) if file_obj.modified_at else '',
                'created_at': str(file_obj.created_at) if file_obj.created_at else '',
                'description': file_obj.description or '',
            }
            if file_obj.modified_by:
                info['modified_by'] = file_obj.modified_by.get('name', '')
            if file_obj.parent:
                info['parent_folder'] = file_obj.parent.get('name', '')
            if file_obj.shared_link:
                info['shared_link'] = file_obj.shared_link.get('url', '')
            # Build full path
            if file_obj.path_collection:
                path_parts = [e['name'] for e in file_obj.path_collection.get('entries', [])]
                info['path'] = '/'.join(path_parts)
            return info
        except Exception as e:
            logger.error(f"Box get_file_info error: {e}")
            return {"error": str(e)}

    def list_folder(self, folder_id='0', limit=50):
        """List contents of a folder. Default '0' is root folder."""
        if not self.client:
            return {"error": "Box client not initialized"}
        try:
            folder = self.client.folder(folder_id)
            folder_info = folder.get(fields=['name'])
            items_iter = folder.get_items(limit=limit, fields=['name', 'type', 'size', 'modified_at'])
            items = []
            for item in items_iter:
                entry = {
                    'id': item.id,
                    'name': item.name,
                    'type': item.type,
                }
                if item.type == 'file':
                    entry['size'] = getattr(item, 'size', None)
                    entry['modified_at'] = str(getattr(item, 'modified_at', ''))
                items.append(entry)
            return {
                'folder_name': folder_info.name,
                'folder_id': folder_id,
                'items': items,
                'count': len(items)
            }
        except Exception as e:
            logger.error(f"Box list_folder error: {e}")
            return {"error": str(e)}

    def get_shared_link(self, file_id, access='open'):
        """Get or create a shared link for a file. Returns the URL."""
        if not self.client:
            return {"error": "Box client not initialized"}
        try:
            file_obj = self.client.file(file_id).get(fields=['shared_link', 'name'])
            # If already has a shared link, return it
            if file_obj.shared_link:
                return {
                    'name': file_obj.name,
                    'url': file_obj.shared_link.get('url', ''),
                    'already_existed': True
                }
            # Create a new shared link
            shared_link = file_obj.get_shared_link(access=access)
            return {
                'name': file_obj.name,
                'url': shared_link,
                'already_existed': False
            }
        except Exception as e:
            logger.error(f"Box get_shared_link error: {e}")
            return {"error": str(e)}

    def get_folder_by_name(self, folder_name, parent_id='0'):
        """Search for a folder by name within a parent folder."""
        if not self.client:
            return {"error": "Box client not initialized"}
        try:
            results = self.client.search().query(
                folder_name,
                result_type='folder',
                limit=5
            )
            matches = []
            for item in results:
                if folder_name.lower() in item.name.lower():
                    matches.append({
                        'id': item.id,
                        'name': item.name,
                    })
                if len(matches) >= 5:
                    break
            return matches
        except Exception as e:
            logger.error(f"Box get_folder_by_name error: {e}")
            return {"error": str(e)}
