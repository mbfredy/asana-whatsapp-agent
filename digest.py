import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def generate_digest(asana_client):
    """Generate a formatted morning digest from Asana data."""
    try:
        parts = []

        now = datetime.now()
        day_name = now.strftime('%A')
        date_str = now.strftime('%B %d, %Y')

        # ── Header ──
        parts.append(f"Good morning, Fredy \u2615\n")
        parts.append(f"\U0001f4c5 *{day_name}, {date_str}*\n")
        parts.append("\u2500" * 20 + "\n")

        # ── My Tasks ──
        my_tasks = asana_client.get_my_tasks()

        due_today = []
        overdue = []
        due_this_week = []
        no_due_date = []

        today_str = now.strftime('%Y-%m-%d')

        for task in my_tasks:
            due_on = task.get('due_on')
            project = task.get('projects', [{}])[0].get('name', 'General') if task.get('projects') else 'General'
            task_name = task['name']
            task_gid = task.get('gid', '')

            if due_on:
                if due_on < today_str:
                    overdue.append((task_name, project, due_on, task_gid))
                elif due_on == today_str:
                    due_today.append((task_name, project, task_gid))
                elif due_on <= (datetime.now().replace(day=now.day + 6)).strftime('%Y-%m-%d'):
                    due_this_week.append((task_name, project, due_on, task_gid))
            else:
                no_due_date.append((task_name, project, task_gid))

        # Overdue (highest priority)
        if overdue:
            parts.append(f"\n\U0001f6a8 *OVERDUE* ({len(overdue)})\n")
            for name, project, due_on, gid in sorted(overdue, key=lambda x: x[2]):
                parts.append(f"   \u26a0\ufe0f {name}\n")
                parts.append(f"      \U0001f4c1 {project}  \u2022  Was due {due_on}\n")

        # Due today
        if due_today:
            parts.append(f"\n\U0001f525 *DUE TODAY* ({len(due_today)})\n")
            for name, project, gid in due_today:
                parts.append(f"   \u27a1\ufe0f {name}\n")
                parts.append(f"      \U0001f4c1 {project}\n")

        # Due this week
        if due_this_week:
            parts.append(f"\n\U0001f4c6 *THIS WEEK* ({len(due_this_week)})\n")
            for name, project, due_on, gid in sorted(due_this_week, key=lambda x: x[2])[:8]:
                parts.append(f"   \u2022 {name}\n")
                parts.append(f"      \U0001f4c1 {project}  \u2022  Due {due_on}\n")

        # No due date
        if no_due_date:
            parts.append(f"\n\u2753 *NO DUE DATE* ({len(no_due_date)})\n")
            for name, project, gid in no_due_date[:5]:
                parts.append(f"   \u2022 {name}\n")
                parts.append(f"      \U0001f4c1 {project}\n")
            if len(no_due_date) > 5:
                parts.append(f"   _...and {len(no_due_date) - 5} more_\n")

        # ── New Tasks (might have missed) ──
        try:
            new_tasks = asana_client.get_new_tasks_assigned(days=1)
            # Filter out tasks we already listed
            known_gids = set()
            for lst in [overdue, due_today]:
                for item in lst:
                    known_gids.add(item[-1])
            for item in due_this_week:
                known_gids.add(item[-1])
            for item in no_due_date:
                known_gids.add(item[-1])

            new_unseen = [t for t in new_tasks if t.get('gid') not in known_gids]

            if new_unseen:
                parts.append(f"\n\U0001f195 *NEW TASKS* ({len(new_unseen)})\n")
                for task in new_unseen[:5]:
                    task_name = task['name']
                    project = task.get('projects', [{}])[0].get('name', '') if task.get('projects') else ''
                    parts.append(f"   \u2022 {task_name}\n")
                    if project:
                        parts.append(f"      \U0001f4c1 {project}\n")
        except Exception as e:
            logger.error(f"Error fetching new tasks for digest: {e}")

        # ── Mentions / Commented On ──
        try:
            mentioned_tasks = asana_client.get_tasks_with_recent_comments(days=2)
            if mentioned_tasks:
                parts.append(f"\n\U0001f4ac *MENTIONS & ACTIVITY*\n")
                for task in mentioned_tasks[:5]:
                    task_name = task['name']
                    project = task.get('projects', [{}])[0].get('name', '') if task.get('projects') else ''
                    parts.append(f"   \u2022 {task_name}")
                    if project:
                        parts.append(f"  ({project})")
                    parts.append("\n")
        except Exception as e:
            logger.error(f"Error fetching mentioned tasks for digest: {e}")

        # ── Risks / Briefs Missing ──
        tasks_no_brief = []
        for task in my_tasks:
            task_name = task.get('name', '')
            # Flag tasks with vague names and no description (we only have name from list endpoint)
            if len(task_name.split()) <= 3 and not task.get('due_on'):
                tasks_no_brief.append(task_name)
        if tasks_no_brief:
            parts.append(f"\n\u26a0\ufe0f *RISKS / WEAK TASKS*\n")
            for name in tasks_no_brief[:5]:
                parts.append(f"   \u2022 {name} \u2014 _vague title, no due date_\n")

        # ── Recently Updated ──
        try:
            recent_tasks = asana_client.get_recent_tasks(days=1)
            if recent_tasks:
                parts.append(f"\n\U0001f504 *RECENTLY UPDATED*\n")
                for task in recent_tasks[:5]:
                    task_name = task['name']
                    project = task.get('projects', [{}])[0].get('name', '') if task.get('projects') else ''
                    parts.append(f"   \u2022 {task_name}")
                    if project:
                        parts.append(f"  ({project})")
                    parts.append("\n")
        except Exception as e:
            logger.error(f"Error fetching recent tasks for digest: {e}")

        # ── Footer ──
        parts.append("\n" + "\u2500" * 20 + "\n")

        total = len(my_tasks)
        urgent = len(overdue) + len(due_today)
        parts.append(f"\U0001f4ca *{total} open tasks*  \u2022  *{urgent} need attention today*\n")

        # Top priority
        if overdue:
            top = overdue[0][0]
            parts.append(f"\n\U0001f3af *Top priority today:* {top}\n")
        elif due_today:
            top = due_today[0][0]
            parts.append(f"\n\U0001f3af *Top priority today:* {top}\n")
        elif due_this_week:
            top = due_this_week[0][0]
            parts.append(f"\n\U0001f3af *Top priority today:* {top}\n")

        parts.append(f"\n\U0001f4ac Reply anytime to ask me about tasks, update them, or assign work.\n")

        digest_text = ''.join(parts)
        logger.info("Digest generated successfully")
        return digest_text

    except Exception as e:
        logger.error(f"Error generating digest: {str(e)}")
        return "\u26a0\ufe0f Unable to generate morning digest at this time. Reply with a message and I'll pull your tasks manually."
