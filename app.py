import os
import json
import logging
from datetime import datetime
from flask import Flask, request, Response
from anthropic import Anthropic
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz

from asana_client import AsanaClient
from digest import generate_digest
from send_whatsapp import send_whatsapp_message

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
asana_client = AsanaClient(config.get('asana_pat'))

# Conversation history storage (per user)
conversation_history = {}
MAX_HISTORY = 20


# ─── Tools Definition for Claude ───

ASANA_TOOLS = [
    {
        "name": "get_my_tasks",
        "description": "Get all incomplete tasks assigned to Fredy. Returns task name, project, due date, and GID.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "get_task_details",
        "description": "Get full details of a specific task including notes/description, assignee, and projects.",
        "input_schema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "string", "description": "The Asana task GID"}
            },
            "required": ["task_id"]
        }
    },
    {
        "name": "get_task_comments",
        "description": "Get the most recent comments on a task.",
        "input_schema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "string", "description": "The Asana task GID"}
            },
            "required": ["task_id"]
        }
    },
    {
        "name": "search_tasks",
        "description": "Search for tasks by keyword. Use this when the user mentions a task by name or topic.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query text"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "update_task",
        "description": "Update a task's name, notes/description, or due date.",
        "input_schema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "string", "description": "The Asana task GID"},
                "name": {"type": "string", "description": "New task name (optional)"},
                "notes": {"type": "string", "description": "New task description/notes (optional)"},
                "due_on": {"type": "string", "description": "New due date in YYYY-MM-DD format (optional)"}
            },
            "required": ["task_id"]
        }
    },
    {
        "name": "complete_task",
        "description": "Mark a task as complete/done.",
        "input_schema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "string", "description": "The Asana task GID"}
            },
            "required": ["task_id"]
        }
    },
    {
        "name": "add_comment",
        "description": "Add a comment to a task. The comment will be posted as Fredy.",
        "input_schema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "string", "description": "The Asana task GID"},
                "text": {"type": "string", "description": "The comment text to post"}
            },
            "required": ["task_id", "text"]
        }
    },
    {
        "name": "assign_task",
        "description": "Assign a task to a team member. First search for the user by name, then assign.",
        "input_schema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "string", "description": "The Asana task GID"},
                "assignee_name": {"type": "string", "description": "Name (or partial name) of the person to assign the task to"}
            },
            "required": ["task_id", "assignee_name"]
        }
    },
    {
        "name": "find_team_member",
        "description": "Look up a team member by name to get their Asana user GID. Use before assigning tasks.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Name or partial name of the person"}
            },
            "required": ["name"]
        }
    },
    {
        "name": "get_recent_activity",
        "description": "Get tasks that were recently modified (last N days).",
        "input_schema": {
            "type": "object",
            "properties": {
                "days": {"type": "integer", "description": "Number of days to look back (default 7)", "default": 7}
            },
            "required": []
        }
    },
    {
        "name": "get_new_tasks",
        "description": "Get newly assigned tasks from the last N days that Fredy might have missed.",
        "input_schema": {
            "type": "object",
            "properties": {
                "days": {"type": "integer", "description": "Number of days to look back (default 1)", "default": 1}
            },
            "required": []
        }
    },
    {
        "name": "get_projects",
        "description": "List all projects in the workspace.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    }
]


SYSTEM_PROMPT = """You are Fredy's AI chief of staff on WhatsApp, connected live to his Asana workspace at DreamFields/Jeeter.

You can READ, UPDATE, COMMENT ON, and ASSIGN tasks in Asana on Fredy's behalf using the tools provided.

FORMAT RULES (this is WhatsApp, not email):
- Use emojis to make things scannable: \U0001f525 urgent, \u2705 done, \U0001f4cb tasks, \u26a0\ufe0f warning, \U0001f4ac comment, \U0001f464 people, \U0001f4c5 dates, \U0001f4c1 projects
- Keep messages short and punchy
- Use line breaks between items for readability
- Use *bold* for emphasis (WhatsApp formatting)
- No markdown headers or code blocks
- When listing tasks, include: emoji + name + project + due date on separate lines
- When confirming an action, be brief: "\u2705 Done! Comment posted on [task name]"

ACTION RULES:
- When Fredy asks to update a task, comment, mark complete, or assign someone: DO IT immediately using the tools. Don't just describe what you would do.
- When Fredy says "comment on X saying Y" - post the comment using add_comment.
- When Fredy says "assign X to [person]" - look up the person first with find_team_member, then assign.
- When Fredy says "mark X as done" or "complete X" - use complete_task.
- When searching for a task, use search_tasks to find it first, then act on the result.
- Always confirm the action after completing it.

BRIEF/DIGEST RULES:
- Briefs should focus on tasks ASSIGNED to Fredy or where he was recently mentioned
- Flag tasks that are overdue or missing descriptions
- Surface new tasks that might have been missed
- Group by urgency: overdue > due today > this week > no date

Fredy's name is Fredy Hernandez. His Asana workspace is DreamFields/Jeeter."""


def execute_tool(tool_name, tool_input):
    """Execute an Asana tool call and return the result."""
    try:
        if tool_name == "get_my_tasks":
            result = asana_client.get_my_tasks()
            return json.dumps(result, default=str)

        elif tool_name == "get_task_details":
            result = asana_client.get_task_details(tool_input["task_id"])
            return json.dumps(result, default=str)

        elif tool_name == "get_task_comments":
            result = asana_client.get_task_stories(tool_input["task_id"])
            return json.dumps(result, default=str)

        elif tool_name == "search_tasks":
            result = asana_client.search_tasks(tool_input["query"])
            return json.dumps(result, default=str)

        elif tool_name == "update_task":
            updates = {}
            for field in ["name", "notes", "due_on"]:
                if field in tool_input and tool_input[field]:
                    updates[field] = tool_input[field]
            result = asana_client.update_task(tool_input["task_id"], updates)
            return json.dumps(result, default=str)

        elif tool_name == "complete_task":
            result = asana_client.complete_task(tool_input["task_id"])
            return json.dumps(result, default=str)

        elif tool_name == "add_comment":
            result = asana_client.add_comment(tool_input["task_id"], tool_input["text"])
            return json.dumps(result, default=str)

        elif tool_name == "assign_task":
            # First find the user
            user = asana_client.find_user_by_name(tool_input["assignee_name"])
            if not user:
                return json.dumps({"error": f"Could not find user matching '{tool_input['assignee_name']}'"})
            result = asana_client.assign_task(tool_input["task_id"], user["gid"])
            return json.dumps({"success": True, "assigned_to": user["name"], "task": result.get("name", "")}, default=str)

        elif tool_name == "find_team_member":
            user = asana_client.find_user_by_name(tool_input["name"])
            if user:
                return json.dumps(user, default=str)
            return json.dumps({"error": f"No user found matching '{tool_input['name']}'"})

        elif tool_name == "get_recent_activity":
            days = tool_input.get("days", 7)
            result = asana_client.get_recent_tasks(days=days)
            return json.dumps(result, default=str)

        elif tool_name == "get_new_tasks":
            days = tool_input.get("days", 1)
            result = asana_client.get_new_tasks_assigned(days=days)
            return json.dumps(result, default=str)

        elif tool_name == "get_projects":
            result = asana_client.get_projects()
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
        add_to_history(user_phone, "user", user_message)
        messages = get_conversation_history(user_phone)

        # Initial Claude call with tools
        response = anthropic_client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1500,
            system=SYSTEM_PROMPT,
            tools=ASANA_TOOLS,
            messages=messages
        )

        # Tool-use loop: keep going until Claude gives a text response
        max_iterations = 8
        iteration = 0

        while response.stop_reason == "tool_use" and iteration < max_iterations:
            iteration += 1

            # Collect all tool uses from the response
            tool_results = []
            assistant_content = response.content

            for block in assistant_content:
                if block.type == "tool_use":
                    tool_name = block.name
                    tool_input = block.input
                    logger.info(f"Tool call: {tool_name}({json.dumps(tool_input)})")

                    result = execute_tool(tool_name, tool_input)
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
                system=SYSTEM_PROMPT,
                tools=ASANA_TOOLS,
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
        # Remove markdown headers but keep WhatsApp bold (*text*)
        line = line.replace('## ', '').replace('### ', '').replace('# ', '')
        formatted.append(line)
    return '\n'.join(formatted)


# ─── Routes ───

@app.route('/webhook', methods=['POST'])
def webhook():
    """Receive WhatsApp messages from Twilio and respond."""
    try:
        incoming_message = request.form.get('Body', '').strip()
        sender_phone = request.form.get('From', '').replace('whatsapp:', '')

        if not incoming_message:
            return Response('', status=200)

        logger.info(f"Received message from {sender_phone}: {incoming_message}")

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

        logger.info(f"Sent {len(chunks)} message(s) to {sender_phone}")
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
        'service': 'asana-whatsapp-agent'
    }, 200


# ─── Digest Scheduler ───

def send_morning_digest():
    """Generate and send morning digest."""
    try:
        logger.info("Generating morning digest...")
        digest_text = generate_digest(asana_client)
        digest_text = format_for_whatsapp(digest_text)

        user_phone = os.getenv('DIGEST_RECIPIENT_PHONE', '+19545042855')

        chunks = split_message(digest_text, max_len=1500)
        for chunk in chunks:
            send_whatsapp_message(
                to_number=user_phone,
                message=chunk,
                config=config
            )

        logger.info("Morning digest sent successfully")
    except Exception as e:
        logger.error(f"Error sending morning digest: {str(e)}")


def init_scheduler():
    scheduler = BackgroundScheduler()
    est = pytz.timezone('US/Eastern')
    scheduler.add_job(
        send_morning_digest,
        CronTrigger(
            hour=10,
            minute=0,
            day_of_week='0-4',
            timezone=est
        ),
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
