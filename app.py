import os
import json
import logging
import threading
from datetime import datetime
from flask import Flask, request, Response
from anthropic import Anthropic
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz

from asana_client import AsanaClient
from digest import generate_digest
from send_whatsapp import send_whatsapp_message

try:
    from box_client import BoxClient
    BOX_AVAILABLE = True
except Exception:
    BoxClient = None
    BOX_AVAILABLE = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)


# ─── Config ───

def load_config():
    config = {}
    env_file = os.path.join(os.path.dirname(__file__), 'config.json')
    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            config = json.load(f)

    config['twilio_account_sid'] = os.getenv('TWILIO_ACCOUNT_SID', config.get('twilio_account_sid'))
    config['twilio_auth_token'] = os.getenv('TWILIO_AUTH_TOKEN', config.get('twilio_auth_token'))
    config['twilio_phone'] = os.getenv('TWILIO_PHONE', config.get('twilio_phone'))
    config['anthropic_api_key'] = os.getenv('ANTHROPIC_API_KEY', config.get('anthropic_api_key'))
    config['asana_pat'] = os.getenv('ASANA_PAT', config.get('asana_pat'))
    return config


config = load_config()
anthropic_client = Anthropic(api_key=config.get('anthropic_api_key'))

# ─── Multi-User Setup ───
# Load user configs: maps "whatsapp:+1XXXXXXXXXX" -> {name, asana_pat, asana_gid}
USERS = {}
try:
    users_json = os.getenv('USERS_CONFIG', '{}')
    USERS = json.loads(users_json)
    logger.info(f"Loaded {len(USERS)} user(s): {[u['name'] for u in USERS.values()]}")
except Exception as e:
    logger.error(f"Error loading USERS_CONFIG: {e}")

# Fallback: if no USERS_CONFIG, use the single ASANA_PAT for the default user
DEFAULT_PHONE = os.getenv('DIGEST_RECIPIENT_PHONE', '+19545042855')
if not USERS:
    USERS[f'whatsapp:{DEFAULT_PHONE}'] = {
        'name': 'Fredy Hernandez',
        'asana_pat': config.get('asana_pat'),
        'asana_gid': '1200045933988109'
    }

# Create an AsanaClient per user (keyed by whatsapp phone key)
user_asana_clients = {}
for phone_key, user_info in USERS.items():
    user_asana_clients[phone_key] = AsanaClient(user_info['asana_pat'])
    logger.info(f"Asana client created for {user_info['name']} ({phone_key})")

# Keep a default client for backward compatibility
asana_client = AsanaClient(config.get('asana_pat'))

# ─── Box Setup ───
box_client = None
if BOX_AVAILABLE:
    box_client_id = os.getenv('BOX_CLIENT_ID')
    box_client_secret = os.getenv('BOX_CLIENT_SECRET')
    box_enterprise_id = os.getenv('BOX_ENTERPRISE_ID')
    box_user_id = os.getenv('BOX_USER_ID')

    if box_client_id and box_client_secret:
        try:
            box_client = BoxClient(
                client_id=box_client_id,
                client_secret=box_client_secret,
                enterprise_id=box_enterprise_id,
                user_id=box_user_id
            )
            logger.info("Box client initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Box client: {e}")
    else:
        logger.info("Box credentials not configured — Box tools disabled")
else:
    logger.info("boxsdk not available — Box tools disabled")

# Conversation history storage (per user)
conversation_history = {}
MAX_HISTORY = 20


def get_user_info(sender_phone):
    """Look up user info by their WhatsApp sender ID (e.g. 'whatsapp:+15617890332' or '+15617890332')."""
    # Try with whatsapp: prefix
    key = f'whatsapp:{sender_phone}' if not sender_phone.startswith('whatsapp:') else sender_phone
    if key in USERS:
        return USERS[key], user_asana_clients[key]
    # Try raw phone
    for k, v in USERS.items():
        if sender_phone in k or k.endswith(sender_phone):
            return v, user_asana_clients[k]
    # Fallback to default (Fredy)
    default_key = f'whatsapp:{DEFAULT_PHONE}'
    return USERS.get(default_key, {'name': 'there'}), asana_client


# ─── Tools Definition for Claude ───

def get_asana_tools(user_name, role="chief_of_staff"):
    """Return tool definitions personalized for the user and role."""
    # PM-specific tools for team-wide visibility
    pm_tools = [
        {
            "name": "get_team_tasks_due_soon",
            "description": "Get ALL tasks across the entire team due within N days. Shows every task with assignee, project, and due date. Essential for PM daily review.",
            "input_schema": {"type": "object", "properties": {"days": {"type": "integer", "description": "Number of days to look ahead (default 5)", "default": 5}}, "required": []}
        },
        {
            "name": "get_team_tasks_overdue",
            "description": "Get ALL overdue tasks across the entire team. Shows who owns each overdue task and which project it belongs to.",
            "input_schema": {"type": "object", "properties": {}, "required": []}
        },
        {
            "name": "get_team_tasks_long_term",
            "description": "Get tasks due between 6-30 days from now. Long-term view for upcoming milestones and deadlines.",
            "input_schema": {"type": "object", "properties": {"start_days": {"type": "integer", "description": "Start of range in days from now (default 6)", "default": 6}, "end_days": {"type": "integer", "description": "End of range in days from now (default 30)", "default": 30}}, "required": []}
        },
        {
            "name": "get_unassigned_tasks",
            "description": "Get all tasks that have no assignee. These need to be triaged and assigned.",
            "input_schema": {"type": "object", "properties": {}, "required": []}
        },
    ]

    base_tools = [
        {
            "name": "get_my_tasks",
            "description": f"Get all incomplete tasks assigned to {user_name}. Returns task name, project, due date, and GID.",
            "input_schema": {"type": "object", "properties": {}, "required": []}
        },
        {
            "name": "get_task_details",
            "description": "Get full details of a specific task including notes/description, assignee, and projects.",
            "input_schema": {"type": "object", "properties": {"task_id": {"type": "string", "description": "The Asana task GID"}}, "required": ["task_id"]}
        },
        {
            "name": "get_task_comments",
            "description": "Get the most recent comments on a task.",
            "input_schema": {"type": "object", "properties": {"task_id": {"type": "string", "description": "The Asana task GID"}}, "required": ["task_id"]}
        },
        {
            "name": "search_tasks",
            "description": "Search for tasks by keyword. Use this when the user mentions a task by name or topic.",
            "input_schema": {"type": "object", "properties": {"query": {"type": "string", "description": "Search query text"}}, "required": ["query"]}
        },
        {
            "name": "update_task",
            "description": "Update a task's name, notes/description, or due date.",
            "input_schema": {"type": "object", "properties": {"task_id": {"type": "string", "description": "The Asana task GID"}, "name": {"type": "string", "description": "New task name (optional)"}, "notes": {"type": "string", "description": "New task description/notes (optional)"}, "due_on": {"type": "string", "description": "New due date in YYYY-MM-DD format (optional)"}}, "required": ["task_id"]}
        },
        {
            "name": "complete_task",
            "description": "Mark a task as complete/done.",
            "input_schema": {"type": "object", "properties": {"task_id": {"type": "string", "description": "The Asana task GID"}}, "required": ["task_id"]}
        },
        {
            "name": "add_comment",
            "description": f"Add a comment to a task. The comment will be posted as {user_name}. To @mention/tag a coworker so they get notified, first use find_team_member to get their user GID, then pass the GID(s) in mention_gids. This creates a real Asana @mention — not just text.",
            "input_schema": {"type": "object", "properties": {"task_id": {"type": "string", "description": "The Asana task GID"}, "text": {"type": "string", "description": "The comment text to post"}, "mention_gids": {"type": "array", "items": {"type": "string"}, "description": "Optional list of user GIDs to @mention/tag in the comment. Use find_team_member first to get GIDs."}}, "required": ["task_id", "text"]}
        },
        {
            "name": "assign_task",
            "description": "Assign a task to a team member. First search for the user by name, then assign.",
            "input_schema": {"type": "object", "properties": {"task_id": {"type": "string", "description": "The Asana task GID"}, "assignee_name": {"type": "string", "description": "Name (or partial name) of the person to assign the task to"}}, "required": ["task_id", "assignee_name"]}
        },
        {
            "name": "find_team_member",
            "description": "Look up a team member by name to get their Asana user GID. Use before assigning tasks.",
            "input_schema": {"type": "object", "properties": {"name": {"type": "string", "description": "Name or partial name of the person"}}, "required": ["name"]}
        },
        {
            "name": "get_recent_activity",
            "description": f"Get tasks that were recently modified (last N days).",
            "input_schema": {"type": "object", "properties": {"days": {"type": "integer", "description": "Number of days to look back (default 7)", "default": 7}}, "required": []}
        },
        {
            "name": "get_new_tasks",
            "description": f"Get newly assigned tasks from the last N days that {user_name} might have missed.",
            "input_schema": {"type": "object", "properties": {"days": {"type": "integer", "description": "Number of days to look back (default 1)", "default": 1}}, "required": []}
        },
        {
            "name": "get_projects",
            "description": "List all projects in the workspace.",
            "input_schema": {"type": "object", "properties": {}, "required": []}
        }
    ]

    # Box tools — only added if Box client is configured
    box_tools = []
    if box_client:
        box_tools = [
            {
                "name": "box_search",
                "description": "Search for files and folders in Box by name or content. Use when the user asks about a document, asset, file, or deliverable stored in Box.",
                "input_schema": {"type": "object", "properties": {"query": {"type": "string", "description": "Search query — file name, keyword, or content"}}, "required": ["query"]}
            },
            {
                "name": "box_get_file_info",
                "description": "Get detailed info about a specific Box file: name, size, who modified it, path, shared link.",
                "input_schema": {"type": "object", "properties": {"file_id": {"type": "string", "description": "The Box file ID"}}, "required": ["file_id"]}
            },
            {
                "name": "box_list_folder",
                "description": "List the contents of a Box folder. Use folder_id '0' for the root. Use box_find_folder first if you only have the folder name.",
                "input_schema": {"type": "object", "properties": {"folder_id": {"type": "string", "description": "The Box folder ID (use '0' for root)", "default": "0"}}, "required": []}
            },
            {
                "name": "box_get_shared_link",
                "description": "Get or create a shareable link for a Box file so the user can open it directly.",
                "input_schema": {"type": "object", "properties": {"file_id": {"type": "string", "description": "The Box file ID"}}, "required": ["file_id"]}
            },
            {
                "name": "box_find_folder",
                "description": "Search for a folder by name in Box. Returns matching folder IDs that can be used with box_list_folder.",
                "input_schema": {"type": "object", "properties": {"folder_name": {"type": "string", "description": "Name of the folder to find"}}, "required": ["folder_name"]}
            },
        ]

    # PM role gets team-wide tools added
    if role == "project_manager":
        return pm_tools + base_tools + box_tools
    return base_tools + box_tools


def get_system_prompt(user_name, role="chief_of_staff", project_name=None):
    """Return the system prompt personalized for the user and their role."""
    first_name = user_name.split()[0]

    if role == "project_manager":
        project_label = f"the *{project_name}* project" if project_name else "all projects"
        return f"""You are {first_name}'s AI project management assistant on WhatsApp, connected live to the Asana workspace at DreamFields/Jeeter.
You can READ, UPDATE, COMMENT ON, and ASSIGN tasks in Asana on {first_name}'s behalf using the tools provided.

ROLE: {first_name} is a *Project Manager*. Her primary board is {project_label}. All team-wide tools (overdue, due soon, long-term, unassigned) are scoped to this project automatically. She needs to see ALL tasks in {project_label} — not just her own.

CORE RESPONSIBILITIES
1. Show {first_name} the full picture across all projects and team members.
2. Surface ALL tasks due within the next 5 days across the team — who owns them, what project, what status.
3. Flag overdue tasks by assignee so she can follow up.
4. Provide a long-term view of upcoming milestones and deadlines beyond 5 days.
5. Identify risks: unassigned tasks, missing due dates, tasks with no brief, blocked work.
6. Take action when {first_name} asks (update, comment, assign, complete).

WHATSAPP FORMAT RULES:
- Use emojis: \U0001f6a8 overdue, \U0001f525 due today, \U0001f4c5 this week, \U0001f4c6 upcoming, \U0001f464 assignee, \U0001f4c1 project, \u26a0\ufe0f risk, \u2705 done, \U0001f195 new
- Keep it scannable. Group by urgency, then by project or assignee.
- Use *bold* for emphasis (WhatsApp formatting).
- No markdown headers or code blocks.
- Always show the *assignee* next to each task — this is critical for a PM.

ACTION RULES:
- When {first_name} asks to update, comment, complete, or assign: DO IT immediately.
- Always confirm the action after completing it.
- When searching, use search_tasks first, then act on results.

DIGEST STRUCTURE (for morning brief / "what's the status"):
1. \U0001f6a8 *OVERDUE* — All overdue tasks across the team, grouped by assignee
2. \U0001f525 *DUE TODAY* — Everything due today, with assignee + project
3. \U0001f4c5 *NEXT 5 DAYS* — All tasks due within 5 days, by date then assignee
4. \U0001f4c6 *LONG-TERM (6-30 days)* — Major deadlines and milestones coming up
5. \u26a0\ufe0f *RISKS* — Unassigned tasks, missing due dates, vague briefs, potential blockers
6. \U0001f195 *NEW / RECENTLY ADDED* — Tasks created in the last 24-48 hours
7. \U0001f4ac *ACTIVITY* — Recent comments, status changes, completed work

End with: \U0001f4ca *Summary:* X tasks due this week, Y overdue, Z unassigned

PRIORITIZATION (PM perspective):
1. Overdue tasks (these are fires)
2. Tasks due within 5 days with issues (no assignee, weak brief)
3. Tasks due within 5 days on track
4. New tasks that need triage
5. Long-term deadlines approaching
6. General activity updates

TONE AND STYLE:
- Project management voice: clear, structured, action-oriented
- Always include who owns each task
- Surface blockers and risks proactively
- Don't sugarcoat — if something is behind, say so directly
- Compress when there's a lot, expand when {first_name} asks for detail

BOX INTEGRATION:
- You also have access to Box (file storage). If {first_name} asks about documents, files, assets, or deliverables, use the box_ tools to search and retrieve info.
- Use box_search to find files, box_get_file_info for details, box_list_folder to browse, and box_get_shared_link to share links.

TAGGING / @MENTIONS:
- When {first_name} asks you to tag or @mention someone on a task, ALWAYS use find_team_member first to get their user GID, then pass it in mention_gids when calling add_comment. This creates a real Asana notification — not just plain text.

BEHAVIOR RULES:
- Do not invent missing information.
- If a task has no assignee, flag it.
- If a task is vague, say why.
- Always address the user as {first_name}."""

    else:
        return f"""You are {first_name}'s AI chief of staff on WhatsApp, connected live to their Asana workspace at DreamFields/Jeeter.
You can READ, UPDATE, COMMENT ON, and ASSIGN tasks in Asana on {first_name}'s behalf using the tools provided.

CORE RESPONSIBILITIES
1. Review all relevant Asana tasks across assigned teams and projects.
2. Identify: newly created tasks, newly updated tasks, tasks with no brief, tasks with incomplete briefs, tasks where {first_name} is the assignee, tasks where {first_name} is mentioned in comments, tasks where {first_name} is added as collaborator/follower, tasks with due date/status/ownership changes that matter.
3. Send structured WhatsApp digests and respond to {first_name}'s requests.
4. Take action on tasks when {first_name} asks (update, comment, assign, complete).

WHATSAPP FORMAT RULES:
- Use emojis: \U0001f525 urgent, \u2705 done, \U0001f4cb tasks, \u26a0\ufe0f warning, \U0001f4ac comment, \U0001f464 people, \U0001f4c5 dates, \U0001f4c1 projects, \U0001f6a8 overdue, \U0001f195 new
- Keep messages short and punchy. This is WhatsApp, not email.
- Use *bold* for emphasis (WhatsApp formatting).
- No markdown headers or code blocks.
- When confirming an action, be brief: "\u2705 Done! Comment posted on [task name]"

ACTION RULES:
- When {first_name} asks to update a task, comment, mark complete, or assign someone: DO IT immediately.
- Always confirm the action after completing it.

BRIEF ANALYSIS RULES:
Mark as *Missing Brief* if: title is vague, description is empty, deliverable unclear.
Mark as *Brief Incomplete* if: some info exists but key parts missing.

DIGEST STRUCTURE:
1. \U0001f6a8 *OVERDUE* — Tasks past due date
2. \U0001f525 *DUE TODAY* — Tasks due today
3. \U0001f4c6 *THIS WEEK* — Tasks due this week
4. \U0001f195 *NEW TASKS* — Recently assigned tasks {first_name} might have missed
5. \U0001f4ac *MENTIONS* — Tasks where {first_name} is mentioned
6. \u26a0\ufe0f *RISKS* — Missing briefs, no assignee, weak tasks
7. \U0001f504 *RECENTLY UPDATED* — Important recent changes

End with: \U0001f3af *Top priority today:* [single most important item]

TONE: Concise, direct, sharp, calm, executive-friendly.

BOX INTEGRATION:
- You also have access to Box (file storage). If {first_name} asks about documents, files, assets, or deliverables, use the box_ tools to search and retrieve info.
- Use box_search to find files, box_get_file_info for details, box_list_folder to browse, and box_get_shared_link to share links.

TAGGING / @MENTIONS:
- When {first_name} asks you to tag or @mention someone on a task, ALWAYS use find_team_member first to get their user GID, then pass it in mention_gids when calling add_comment. This creates a real Asana notification — not just plain text.

BEHAVIOR RULES:
- Do not invent missing information.
- If a task is weak, say exactly why.
- If something is blocked or at risk, say so clearly.
- Always address the user as {first_name}."""


def execute_tool(tool_name, tool_input, user_asana, project_gid=None):
    """Execute an Asana tool call and return the result. Uses the per-user Asana client."""
    try:
        if tool_name == "get_my_tasks":
            result = user_asana.get_my_tasks()
            return json.dumps(result, default=str)
        elif tool_name == "get_task_details":
            result = user_asana.get_task_details(tool_input["task_id"])
            return json.dumps(result, default=str)
        elif tool_name == "get_task_comments":
            result = user_asana.get_task_stories(tool_input["task_id"])
            return json.dumps(result, default=str)
        elif tool_name == "search_tasks":
            result = user_asana.search_tasks(tool_input["query"])
            return json.dumps(result, default=str)
        elif tool_name == "update_task":
            updates = {}
            for field in ["name", "notes", "due_on"]:
                if field in tool_input and tool_input[field]:
                    updates[field] = tool_input[field]
            result = user_asana.update_task(tool_input["task_id"], updates)
            return json.dumps(result, default=str)
        elif tool_name == "complete_task":
            result = user_asana.complete_task(tool_input["task_id"])
            return json.dumps(result, default=str)
        elif tool_name == "add_comment":
            mention_gids = tool_input.get("mention_gids", None)
            result = user_asana.add_comment(tool_input["task_id"], tool_input["text"], mention_gids=mention_gids)
            return json.dumps(result, default=str)
        elif tool_name == "assign_task":
            user = user_asana.find_user_by_name(tool_input["assignee_name"])
            if not user:
                return json.dumps({"error": f"Could not find user matching '{tool_input['assignee_name']}'"})
            result = user_asana.assign_task(tool_input["task_id"], user["gid"])
            return json.dumps({"success": True, "assigned_to": user["name"], "task": result.get("name", "")}, default=str)
        elif tool_name == "find_team_member":
            user = user_asana.find_user_by_name(tool_input["name"])
            if user:
                return json.dumps(user, default=str)
            return json.dumps({"error": f"No user found matching '{tool_input['name']}'"})
        elif tool_name == "get_recent_activity":
            days = tool_input.get("days", 7)
            result = user_asana.get_recent_tasks(days=days)
            return json.dumps(result, default=str)
        elif tool_name == "get_new_tasks":
            days = tool_input.get("days", 1)
            result = user_asana.get_new_tasks_assigned(days=days)
            return json.dumps(result, default=str)
        elif tool_name == "get_projects":
            result = user_asana.get_projects()
            return json.dumps(result, default=str)
        # PM-specific tools (scoped to project if configured)
        elif tool_name == "get_team_tasks_due_soon":
            days = tool_input.get("days", 5)
            result = user_asana.get_team_tasks_due_soon(days=days, project_gid=project_gid)
            return json.dumps(result, default=str)
        elif tool_name == "get_team_tasks_overdue":
            result = user_asana.get_team_tasks_overdue(project_gid=project_gid)
            return json.dumps(result, default=str)
        elif tool_name == "get_team_tasks_long_term":
            start_days = tool_input.get("start_days", 6)
            end_days = tool_input.get("end_days", 30)
            result = user_asana.get_team_tasks_long_term(start_days=start_days, end_days=end_days, project_gid=project_gid)
            return json.dumps(result, default=str)
        elif tool_name == "get_unassigned_tasks":
            result = user_asana.get_unassigned_tasks(project_gid=project_gid)
            return json.dumps(result, default=str)
        # ─── Box Tools ───
        elif tool_name == "box_search":
            if not box_client:
                return json.dumps({"error": "Box is not configured"})
            result = box_client.search(tool_input["query"])
            return json.dumps(result, default=str)
        elif tool_name == "box_get_file_info":
            if not box_client:
                return json.dumps({"error": "Box is not configured"})
            result = box_client.get_file_info(tool_input["file_id"])
            return json.dumps(result, default=str)
        elif tool_name == "box_list_folder":
            if not box_client:
                return json.dumps({"error": "Box is not configured"})
            folder_id = tool_input.get("folder_id", "0")
            result = box_client.list_folder(folder_id)
            return json.dumps(result, default=str)
        elif tool_name == "box_get_shared_link":
            if not box_client:
                return json.dumps({"error": "Box is not configured"})
            result = box_client.get_shared_link(tool_input["file_id"])
            return json.dumps(result, default=str)
        elif tool_name == "box_find_folder":
            if not box_client:
                return json.dumps({"error": "Box is not configured"})
            result = box_client.get_folder_by_name(tool_input["folder_name"])
            return json.dumps(result, default=str)
        else:
            return json.dumps({"error": f"Unknown tool: {tool_name}"})
    except Exception as e:
        logger.error(f"Tool execution error ({tool_name}): {str(e)}")
        return json.dumps({"error": str(e)})


# ─── Conversation ───

def get_conversation_history(user_phone):
    if user_phone not in conversation_history:
        conversation_history[user_phone] = []
    return conversation_history[user_phone]


def add_to_history(user_phone, role, content):
    history = get_conversation_history(user_phone)
    history.append({"role": role, "content": content})
    if len(history) > MAX_HISTORY:
        conversation_history[user_phone] = history[-MAX_HISTORY:]


def process_message_with_claude(user_message, user_phone):
    """Process user message with Claude using tool-use for Asana actions."""
    try:
        # Look up who's messaging and get their personalized Asana client
        user_info, user_asana = get_user_info(user_phone)
        user_name = user_info.get('name', 'there')
        logger.info(f"Processing message for {user_name} ({user_phone})")

        add_to_history(user_phone, "user", user_message)
        messages = get_conversation_history(user_phone)

        # Get personalized system prompt and tools for this user
        user_role = user_info.get('role', 'chief_of_staff')
        user_project_gid = user_info.get('project_gid', None)
        user_project_name = user_info.get('project_name', None)
        system_prompt = get_system_prompt(user_name, role=user_role, project_name=user_project_name)
        tools = get_asana_tools(user_name, role=user_role)

        # Initial Claude call with tools
        response = anthropic_client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1500,
            system=system_prompt,
            tools=tools,
            messages=messages
        )

        # Tool-use loop: keep going until Claude gives a text response
        max_iterations = 8
        iteration = 0

        while response.stop_reason == "tool_use" and iteration < max_iterations:
            iteration += 1
            tool_results = []
            assistant_content = response.content

            for block in assistant_content:
                if block.type == "tool_use":
                    tool_name = block.name
                    tool_input = block.input
                    logger.info(f"[{user_name}] Tool call: {tool_name}({json.dumps(tool_input)})")

                    result = execute_tool(tool_name, tool_input, user_asana, project_gid=user_project_gid)
                    logger.info(f"Tool result preview: {result[:200]}")

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result
                    })

            # Add assistant message + tool results to history
            add_to_history(user_phone, "assistant", assistant_content)
            add_to_history(user_phone, "user", tool_results)

            # Call Claude again with the tool results
            response = anthropic_client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=1500,
                system=system_prompt,
                tools=tools,
                messages=get_conversation_history(user_phone)
            )

        # Extract final text response
        final_text = ""
        for block in response.content:
            if hasattr(block, "text"):
                final_text += block.text

        if not final_text:
            final_text = "\u2705 Done!"

        # Save the final assistant response in a clean format for history
        add_to_history(user_phone, "assistant", final_text)
        return final_text

    except Exception as e:
        logger.error(f"Error processing message with Claude: {str(e)}")
        return "\u26a0\ufe0f Sorry, I hit an error. Try again in a sec."


def format_for_whatsapp(text):
    """Light formatting cleanup for WhatsApp."""
    lines = text.split('\n')
    formatted = []
    for line in lines:
        line = line.replace('## ', '').replace('### ', '').replace('# ', '')
        formatted.append(line)
    return '\n'.join(formatted)


def process_and_reply(incoming_message, sender_phone):
    """Background worker: process message with Claude and send reply via WhatsApp."""
    try:
        logger.info(f"[BG] Processing message for {sender_phone}: {incoming_message[:80]}")
        response_text = process_message_with_claude(incoming_message, sender_phone)
        response_text = format_for_whatsapp(response_text)

        # WhatsApp has a 1600 char limit per message — split if needed
        chunks = split_message(response_text, max_len=1500)
        for chunk in chunks:
            send_whatsapp_message(
                to_number=sender_phone,
                message=chunk,
                config=config
            )

        logger.info(f"[BG] Sent {len(chunks)} message(s) to {sender_phone}")
    except Exception as e:
        logger.error(f"[BG] Error processing message for {sender_phone}: {str(e)}")
        # Try to send an error message back
        try:
            send_whatsapp_message(
                to_number=sender_phone,
                message="\u26a0\ufe0f Sorry, I hit an error processing your message. Try again in a sec.",
                config=config
            )
        except Exception:
            logger.error(f"[BG] Failed to send error message to {sender_phone}")


# ─── Routes ───

@app.route('/webhook', methods=['POST'])
def webhook():
    """Receive WhatsApp messages from Twilio and respond asynchronously."""
    try:
        incoming_message = request.form.get('Body', '').strip()
        sender_phone = request.form.get('From', '').replace('whatsapp:', '')

        if not incoming_message:
            return Response('', status=200)

        logger.info(f"Received message from {sender_phone}: {incoming_message}")

        # Process in background thread so we return 200 to Twilio immediately.
        # This prevents gunicorn worker timeouts and Twilio retry storms.
        thread = threading.Thread(
            target=process_and_reply,
            args=(incoming_message, sender_phone),
            daemon=True
        )
        thread.start()

        # Return 200 immediately — Twilio is happy, worker is free
        return Response('', status=200)

    except Exception as e:
        logger.error(f"Error in webhook: {str(e)}")
        return Response('Error processing message', status=500)


def split_message(text, max_len=1500):
    """Split a long message into WhatsApp-friendly chunks."""
    if len(text) <= max_len:
        return [text]
    chunks = []
    lines = text.split('\n')
    current_chunk = ""
    for line in lines:
        if len(current_chunk) + len(line) + 1 > max_len:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = line + '\n'
        else:
            current_chunk += line + '\n'
    if current_chunk.strip():
        chunks.append(current_chunk.strip())
    return chunks if chunks else [text[:max_len]]


@app.route('/health', methods=['GET'])
def health():
    return {
        'status': 'ok',
        'timestamp': datetime.utcnow().isoformat(),
        'service': 'asana-whatsapp-agent',
        'users': len(USERS)
    }, 200


# ─── Digest Scheduler (Multi-User) ───

def send_morning_digest():
    """Generate and send morning digest to ALL registered users."""
    try:
        for phone_key, user_info in USERS.items():
            user_name = user_info['name']
            user_phone = phone_key.replace('whatsapp:', '')
            user_asana = user_asana_clients[phone_key]

            user_role = user_info.get('role', 'chief_of_staff')
            user_project_gid = user_info.get('project_gid', None)
            user_project_name = user_info.get('project_name', None)
            logger.info(f"Generating morning digest for {user_name} (role: {user_role}, project: {user_project_name})...")
            digest_text = generate_digest(user_asana, user_name=user_name, role=user_role, project_gid=user_project_gid, project_name=user_project_name)
            digest_text = format_for_whatsapp(digest_text)

            chunks = split_message(digest_text, max_len=1500)
            for chunk in chunks:
                send_whatsapp_message(
                    to_number=user_phone,
                    message=chunk,
                    config=config
                )
            logger.info(f"Morning digest sent to {user_name} ({user_phone})")

    except Exception as e:
        logger.error(f"Error sending morning digest: {str(e)}")


def init_scheduler():
    scheduler = BackgroundScheduler()
    est = pytz.timezone('US/Eastern')
    scheduler.add_job(
        send_morning_digest,
        CronTrigger(hour=10, minute=0, day_of_week='0-4', timezone=est),
        id='morning_digest',
        name='Send morning digest',
        replace_existing=True
    )
    scheduler.start()
    logger.info("Scheduler initialized - digest at 10:00 AM EST weekdays")
    return scheduler


# Initialize scheduler when module is loaded (works with gunicorn)
scheduler = init_scheduler()

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
