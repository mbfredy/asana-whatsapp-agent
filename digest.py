import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def generate_digest(asana_client):
    """Generate morning digest from Asana data."""
    try:
        digest_parts = []
        
        # Header
        now = datetime.now()
        day_name = now.strftime('%A')
        digest_parts.append(f"Good morning, Fredy\n\n--- {day_name}, {now.strftime('%B %d')} ---\n")
        
        # Get my tasks
        my_tasks = asana_client.get_my_tasks()
        
        if my_tasks:
            digest_parts.append("YOUR TASKS TODAY:\n")
            
            # Separate by due date
            due_today = []
            due_this_week = []
            no_due_date = []
            
            for task in my_tasks:
                due_on = task.get('due_on')
                project = task.get('projects', [{}])[0].get('name', 'General') if task.get('projects') else 'General'
                task_name = task['name']
                
                if due_on == now.strftime('%Y-%m-%d'):
                    due_today.append((task_name, project))
                elif due_on and due_on > now.strftime('%Y-%m-%d'):
                    due_this_week.append((task_name, project, due_on))
                else:
                    no_due_date.append((task_name, project))
            
            # List due today first (with emphasis)
            if due_today:
                digest_parts.append("⚠ DUE TODAY:\n")
                for name, project in due_today:
                    digest_parts.append(f"  • {name} ({project})\n")
                digest_parts.append("\n")
            
            # Due this week
            if due_this_week:
                digest_parts.append("THIS WEEK:\n")
                for name, project, due_on in sorted(due_this_week, key=lambda x: x[2])[:5]:
                    digest_parts.append(f"  • {name} ({project}) - Due {due_on}\n")
                digest_parts.append("\n")
            
            # No due date (flag these)
            if no_due_date:
                digest_parts.append("NO DUE DATE (flagged):\n")
                for name, project in no_due_date[:5]:
                    digest_parts.append(f"  • {name} ({project})\n")
                digest_parts.append("\n")
        
        # Get recent activity
        recent_tasks = asana_client.get_recent_tasks(days=1)
        
        if recent_tasks:
            digest_parts.append("RECENTLY UPDATED:\n")
            for task in recent_tasks[:5]:
                task_name = task['name']
                project = task.get('projects', [{}])[0].get('name', 'General') if task.get('projects') else 'General'
                digest_parts.append(f"  • {task_name} ({project})\n")
            digest_parts.append("\n")
        
        # Summary
        digest_parts.append("\nFocus on what matters. Let me know if you need anything.\n")
        
        digest_text = ''.join(digest_parts)
        logger.info("Digest generated successfully")
        return digest_text
    
    except Exception as e:
        logger.error(f"Error generating digest: {str(e)}")
        return "Unable to generate morning digest at this time."
