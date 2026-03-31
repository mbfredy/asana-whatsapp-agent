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

# Load configuration
def load_config():
    config = {}
    env_file = os.path.join(os.path.dirname(__file__), 'config.json')
    
    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            config = json.load(f)
    
    # Environment variables take precedence
    config['twilio_account_sid'] = os.getenv('TWILIO_ACCOUNT_SID', config.get('twilio_account_sid'))
    config['twilio_auth_token'] = os.getenv('TWILIO_AUTH_TOKEN', config.get('twilio_auth_token'))
    config['twilio_phone'] = os.getenv('TWILIO_PHONE', config.get('twilio_phone'))
    config['anthropic_api_key'] = os.getenv('ANTHROPIC_API_KEY', config.get('anthropic_api_key'))
    config['asana_pat'] = os.getenv('ASANA_PAT', config.get('asana_pat'))
    
    return config

config = load_config()

# Initialize clients
anthropic_client = Anthropic(api_key=config.get('anthropic_api_key'))
asana_client = AsanaClient(config.get('asana_pat'))

# Conversation history storage (per user, last 20 messages)
conversation_history = {}
MAX_HISTORY = 20

SYSTEM_PROMPT = """You are an AI operations assistant connected to Asana. You act like a sharp chief of staff for a senior creative/operations leader at DreamFields/Jeeter. Your job is to monitor Asana activity, surface risks, summarize asks, and help leadership stay on top of what matters.

You have access to the user's Asana data which will be provided to you. When the user asks about tasks, projects, deadlines, or anything work-related, analyze the Asana data provided and give concise, actionable answers.

Core rules:
- Be concise and direct. This is WhatsApp, not email.
- Lead with what matters. No filler.
- If something is blocked or at risk, say so clearly.
- If a task has no brief, call it out.
- Format for mobile reading — short paragraphs, line breaks between items.
- Use plain text, no markdown. Minimal emojis.
- When listing tasks, include: name, project, due date, status, and any flags.
- Prioritize: tasks assigned to the user > tasks missing briefs > mentions > general updates.

The user's name is Fredy Hernandez. Their Asana email is fh@dreamfields.com."""


def get_asana_context():
    """Fetch current Asana data and format as context for Claude."""
    try:
        my_tasks = asana_client.get_my_tasks()
        recent_tasks = asana_client.get_recent_tasks(days=7)
        
        context = "CURRENT ASANA DATA:\n\n"
        
        if my_tasks:
            context += "TASKS ASSIGNED TO ME:\n"
            for task in my_tasks:
                due_date = task.get('due_on', 'No due date')
                project = task.get('projects', [{}])[0].get('name', 'Unknown') if task.get('projects') else 'Unknown'
                context += f"- {task['name']} (Project: {project}, Due: {due_date})\n"
            context += "\n"
        
        if recent_tasks:
            context += "RECENTLY MODIFIED (Last 7 days):\n"
            for task in recent_tasks[:10]:  # Limit to 10 most recent
                context += f"- {task['name']}\n"
            context += "\n"
        
        return context
    except Exception as e:
        logger.error(f"Error fetching Asana context: {str(e)}")
        return "Unable to fetch current Asana data.\n\n"


def get_conversation_history(user_phone):
    """Get conversation history for a user, or initialize if not present."""
    if user_phone not in conversation_history:
        conversation_history[user_phone] = []
    return conversation_history[user_phone]


def add_to_history(user_phone, role, content):
    """Add a message to conversation history."""
    history = get_conversation_history(user_phone)
    history.append({"role": role, "content": content})
    
    # Keep only last 20 messages
    if len(history) > MAX_HISTORY:
        conversation_history[user_phone] = history[-MAX_HISTORY:]


def process_message_with_claude(user_message, user_phone):
    """Process user message with Claude, including Asana context."""
    try:
        # Get current Asana context
        asana_context = get_asana_context()
        
        # Add user message to history
        add_to_history(user_phone, "user", user_message)
        
        # Prepare messages for Claude (system prompt + asana context + conversation)
        messages_for_claude = get_conversation_history(user_phone)
        
        # Call Claude with Asana context
        response = anthropic_client.messages.create(
            model="claude-sonnet-4-5-20250514",
            max_tokens=1024,
            system=SYSTEM_PROMPT + "\n\n" + asana_context,
            messages=messages_for_claude
        )
        
        assistant_message = response.content[0].text
        
        # Add assistant response to history
        add_to_history(user_phone, "assistant", assistant_message)
        
        return assistant_message
    except Exception as e:
        logger.error(f"Error processing message with Claude: {str(e)}")
        return "Sorry, I encountered an error processing your message. Please try again."


def format_for_whatsapp(text):
    """Format text for WhatsApp display (remove markdown, limit line length)."""
    # Remove markdown headers
    lines = text.split('\n')
    formatted_lines = []
    for line in lines:
        # Remove markdown formatting
        line = line.replace('**', '').replace('##', '').replace('###', '')
        formatted_lines.append(line)
    
    return '\n'.join(formatted_lines)


@app.route('/webhook', methods=['POST'])
def webhook():
    """Receive WhatsApp messages from Twilio and respond."""
    try:
        # Twilio sends form data, not JSON
        incoming_message = request.form.get('Body', '').strip()
        sender_phone = request.form.get('From', '').replace('whatsapp:', '')
        
        if not incoming_message:
            return Response('', status=200)
        
        logger.info(f"Received message from {sender_phone}: {incoming_message}")
        
        # Process message with Claude
        response_text = process_message_with_claude(incoming_message, sender_phone)
        
        # Format for WhatsApp
        response_text = format_for_whatsapp(response_text)
        
        # Send response back via Twilio
        send_whatsapp_message(
            to_number=sender_phone,
            message=response_text,
            config=config
        )
        
        logger.info(f"Sent response to {sender_phone}")
        return Response('', status=200)
        
    except Exception as e:
        logger.error(f"Error in webhook: {str(e)}")
        return Response('Error processing message', status=500)


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return {
        'status': 'ok',
        'timestamp': datetime.utcnow().isoformat(),
        'service': 'asana-whatsapp-agent'
    }, 200


def send_morning_digest():
    """Generate and send morning digest."""
    try:
        logger.info("Generating morning digest...")
        digest_text = generate_digest(asana_client)
        
        # Format for WhatsApp
        digest_text = format_for_whatsapp(digest_text)
        
        # Send to user (using the configured phone for testing)
        # In production, this would query a user preferences table
        user_phone = os.getenv('DIGEST_RECIPIENT_PHONE', '+19545042855')
        
        send_whatsapp_message(
            to_number=user_phone,
            message=digest_text,
            config=config
        )
        
        logger.info("Morning digest sent successfully")
    except Exception as e:
        logger.error(f"Error sending morning digest: {str(e)}")


def init_scheduler():
    """Initialize APScheduler for digest delivery."""
    scheduler = BackgroundScheduler()
    
    # Schedule digest for 10:00 AM EST every weekday (Mon-Fri)
    est = pytz.timezone('US/Eastern')
    scheduler.add_job(
        send_morning_digest,
        CronTrigger(
            hour=10,
            minute=0,
            day_of_week='0-4',  # Monday to Friday
            timezone=est
        ),
        id='morning_digest',
        name='Send morning digest',
        replace_existing=True
    )
    
    scheduler.start()
    logger.info("Scheduler initialized and running")
    
    return scheduler


if __name__ == '__main__':
    # Initialize scheduler
    scheduler = init_scheduler()
    
    # Run Flask app
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
