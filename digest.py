import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def generate_pm_digest(asana_client, user_name="Daniella Aservi"):
    """Generate a PM-focused morning digest: team-wide tasks due within 5 days + long-term."""
    try:
        parts = []
        first_name = user_name.split()[0]
        now = datetime.now()
        day_name = now.strftime('%A')
        date_str = now.strftime('%B %d, %Y')
        today_str = now.strftime('%Y-%m-%d')

        parts.append(f"Good morning, {first_name} \u2615\n")
        parts.append(f"\U0001f4c5 *{day_name}, {date_str}*\n")
        parts.append("\u2500" * 20 + "\n")

        # ── Overdue (team-wide) ──
        try:
            overdue = asana_client.get_team_tasks_overdue()
            if overdue:
                parts.append(f"\n\U0001f6a8 *OVERDUE* ({len(overdue)})\n")
                by_assignee = {}
                for t in overdue:
                    assignee = t.get('assignee', {})
                    name = assignee.get('name', 'Unassigned') if assignee else 'Unassigned'
                    by_assignee.setdefault(name, []).append(t)
                for assignee, tasks in sorted(by_assignee.items()):
                    parts.append(f"\n   \U0001f464 *{assignee}*\n")
                    for t in tasks[:5]:
                        project = t.get('projects', [{}])[0].get('name', '') if t.get('projects') else ''
                        parts.append(f"      \u26a0\ufe0f {t['name']}\n")
                        parts.append(f"         Due {t.get('due_on', '?')}  \u2022  {project}\n")
        except Exception as e:
            logger.error(f"PM digest overdue error: {e}")

        # ── Due within 5 days (team-wide) ──
        try:
            due_soon = asana_client.get_team_tasks_due_soon(days=5)
            due_today = [t for t in due_soon if t.get('due_on') == today_str]
            due_rest = [t for t in due_soon if t.get('due_on') and t.get('due_on') != today_str]

            if due_today:
                parts.append(f"\n\U0001f525 *DUE TODAY* ({len(due_today)})\n")
                for t in due_today:
                    assignee = t.get('assignee', {})
                    name = assignee.get('name', 'Unassigned') if assignee else 'Unassigned'
                    project = t.get('projects', [{}])[0].get('name', '') if t.get('projects') else ''
                    parts.append(f"   \u27a1\ufe0f {t['name']}\n")
                    parts.append(f"      \U0001f464 {name}  \u2022  \U0001f4c1 {project}\n")

            if due_rest:
                parts.append(f"\n\U0001f4c5 *NEXT 5 DAYS* ({len(due_rest)})\n")
                for t in sorted(due_rest, key=lambda x: x.get('due_on', ''))[:15]:
                    assignee = t.get('assignee', {})
                    name = assignee.get('name', 'Unassigned') if assignee else 'Unassigned'
                    project = t.get('projects', [{}])[0].get('name', '') if t.get('projects') else ''
                    parts.append(f"   \u2022 {t['name']}\n")
                    parts.append(f"      \U0001f464 {name}  \u2022  Due {t.get('due_on')}  \u2022  {project}\n")
                if len(due_rest) > 15:
                    parts.append(f"   _...and {len(due_rest) - 15} more_\n")
        except Exception as e:
            logger.error(f"PM digest due-soon error: {e}")

        # ── Long-term (6-30 days) ──
        try:
            long_term = asana_client.get_team_tasks_long_term(start_days=6, end_days=30)
            if long_term:
                parts.append(f"\n\U0001f4c6 *UPCOMING (6-30 DAYS)* ({len(long_term)})\n")
                for t in long_term[:10]:
                    assignee = t.get('assignee', {})
                    name = assignee.get('name', 'Unassigned') if assignee else 'Unassigned'
                    project = t.get('projects', [{}])[0].get('name', '') if t.get('projects') else ''
                    parts.append(f"   \u2022 {t['name']}\n")
                    parts.append(f"      \U0001f464 {name}  \u2022  Due {t.get('due_on')}  \u2022  {project}\n")
                if len(long_term) > 10:
                    parts.append(f"   _...and {len(long_term) - 10} more_\n")
        except Exception as e:
            logger.error(f"PM digest long-term error: {e}")

        # ── Risks: unassigned tasks ──
        try:
            unassigned = asana_client.get_unassigned_tasks()
            if unassigned:
                parts.append(f"\n\u26a0\ufe0f *NEEDS ASSIGNMENT* ({len(unassigned)})\n")
                for t in unassigned[:8]:
                    project = t.get('projects', [{}])[0].get('name', '') if t.get('projects') else ''
                    due = t.get('due_on', 'No date')
                    parts.append(f"   \u2022 {t['name']}\n")
                    parts.append(f"      {project}  \u2022  {due}\n")
        except Exception as e:
            logger.error(f"PM digest unassigned error: {e}")

        # ── Recently updated ──
        try:
            recent = asana_client.get_recent_tasks(days=1)
            if recent:
                parts.append(f"\n\U0001f504 *RECENTLY UPDATED*\n")
                for t in recent[:5]:
                    project = t.get('projects', [{}])[0].get('name', '') if t.get('projects') else ''
                    assignee = t.get('assignee', {})
                    name = assignee.get('name', '') if assignee else ''
                    parts.append(f"   \u2022 {t['name']}")
                    if name:
                        parts.append(f"  ({name})")
                    if project:
                        parts.append(f"  \u2022  {project}")
                    parts.append("\n")
        except Exception as e:
            logger.error(f"PM digest recent error: {e}")

        # ── Footer / Summary ──
        parts.append("\n" + "\u2500" * 20 + "\n")
        overdue_count = len(overdue) if 'overdue' in dir() else 0
        due_soon_count = len(due_soon) if 'due_soon' in dir() else 0
        unassigned_count = len(unassigned) if 'unassigned' in dir() else 0
        parts.append(f"\U0001f4ca *Summary:* {due_soon_count} tasks due within 5 days  \u2022  {overdue_count} overdue  \u2022  {unassigned_count} unassigned\n")
        parts.append(f"\n\U0001f4ac Reply anytime to ask about tasks, reassign work, or check on specific projects.\n")

        return ''.join(parts)

    except Exception as e:
        logger.error(f"Error generating PM digest: {str(e)}")
        return "\u26a0\ufe0f Unable to generate morning digest. Reply with a message and I'll pull the info manually."


def generate_digest(asana_client, user_name="Fredy Hernandez", role="chief_of_staff"):
    """Generate a formatted morning digest from Asana data."""
    if role == "project_manager":
        return generate_pm_digest(asana_client, user_name=user_name)
    try:
        parts = []
        first_name = user_name.split()[0]

        now = datetime.now()
        day_name = now.strftime('%A')
        date_str = now.strftime('%B %d, %Y')

        # ── Header ──
        parts.append(f"Good morning, {first_name} \u2615\n")
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
