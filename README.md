# Asana WhatsApp AI Agent

An interactive WhatsApp AI assistant powered by Claude and connected to Asana. Acts as a sharp chief of staff for managing tasks and projects.

## Features

- Real-time WhatsApp messaging via Twilio
- Claude-powered AI responses with Asana integration
- Automatic morning task digest (10 AM EST, weekdays)
- Task search and filtering
- Conversation history per user
- Production-ready deployment

## Prerequisites

- Python 3.8+
- Twilio account with WhatsApp Business Account setup
- Anthropic API key (Claude Sonnet 4.5)
- Asana Personal Access Token
- Ngrok or similar for local webhook testing

## Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Credentials

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

Or update `config.json` with:
- Twilio Account SID
- Twilio Auth Token
- Twilio WhatsApp Phone Number
- Anthropic API Key
- Asana Personal Access Token

### 3. Getting Credentials

**Twilio:**
1. Create account at https://www.twilio.com
2. Go to Messaging > Try it out > Send a WhatsApp message
3. Copy Account SID and Auth Token from console
4. Set up WhatsApp Sandbox or connect Business Account

**Anthropic:**
1. Create account at https://console.anthropic.com
2. Create API key in Settings
3. Add to `.env` as `ANTHROPIC_API_KEY`

**Asana:**
1. Log in to Asana
2. Go to Settings > Personal Access Tokens
3. Create new token
4. Add to `.env` as `ASANA_PAT`

### 4. Set Up Webhook

For local testing with Ngrok:

```bash
ngrok http 5000
```

For production (Railway/Render):
- Deploy this repo
- Set environment variables in dashboard
- Twilio webhook URL: `https://your-app.com/webhook`

### 5. Configure Twilio Webhook

1. Go to Twilio Console > Messaging > Settings > WhatsApp Sandbox
2. Set "When a message comes in" URL to: `https://your-domain.com/webhook`
3. Method: POST

## Running Locally

```bash
python app.py
```

The app will start on `http://localhost:5000`

Test webhook: `curl http://localhost:5000/health`

## Deployment

### Railway

1. Push to GitHub
2. Create new project on Railway
3. Add repository
4. Set environment variables
5. Deploy (Procfile auto-detected)

### Render

1. Connect GitHub repository
2. Create new Web Service
3. Set environment variables
4. Build command: `pip install -r requirements.txt`
5. Start command: `gunicorn app:app`

## Architecture

### app.py
- Flask server with Twilio webhook
- Claude message processing
- Conversation history management
- APScheduler for morning digest
- Health check endpoint

### asana_client.py
- Asana REST API wrapper
- Task fetching and filtering
- Search functionality
- User information retrieval

### digest.py
- Morning digest generation
- Task prioritization
- Formatted WhatsApp output

### send_whatsapp.py
- Twilio message sending
- Error handling

## Usage

Send a WhatsApp message to your Twilio number:

```
What are my tasks today?
```

The assistant will:
1. Fetch your current Asana tasks
2. Provide context to Claude
3. Generate a concise, mobile-friendly response
4. Send back via WhatsApp

## Example Conversations

**User:** "What's due today?"
**Bot:** Lists tasks due today with priority flags

**User:** "Search for design tasks"
**Bot:** Returns design-related tasks from Asana

**User:** "Give me a summary of this week"
**Bot:** Provides task overview with deadlines

## Morning Digest

Runs automatically at 10:00 AM EST on weekdays. Includes:
- Tasks due today
- This week's tasks
- Tasks without due dates (flagged)
- Recent activity

## Environment Variables

```
TWILIO_ACCOUNT_SID       - Twilio Account SID
TWILIO_AUTH_TOKEN        - Twilio Auth Token
TWILIO_PHONE             - Twilio WhatsApp Phone (e.g., +1234567890)
ANTHROPIC_API_KEY        - Anthropic API Key
ASANA_PAT                - Asana Personal Access Token
PORT                     - Server port (default: 5000)
DIGEST_RECIPIENT_PHONE   - Phone number for digest (testing only)
FLASK_ENV                - Flask environment (production/development)
```

## Troubleshooting

### Webhook not receiving messages
- Verify Twilio webhook URL is public and correct
- Check that POST method is selected
- Test with Twilio's WhatsApp Sandbox message

### Claude API errors
- Verify `ANTHROPIC_API_KEY` is correct
- Check API key has access to Claude Sonnet 4.5
- Review rate limits

### Asana API errors
- Verify `ASANA_PAT` is valid
- Ensure token has access to tasks
- Check Asana workspace permissions

### Scheduler not running
- Verify APScheduler dependency installed
- Check Flask is running (scheduler requires app context)
- Confirm timezone settings (EST for digest)

## API Endpoints

### POST /webhook
Receives WhatsApp messages from Twilio
- Request: Form data from Twilio
- Response: 200 OK (message processed asynchronously)

### GET /health
Health check endpoint
- Response: JSON with status and timestamp

## Production Checklist

- [ ] Environment variables configured in deployment platform
- [ ] Twilio webhook URL updated to production domain
- [ ] Anthropic API key has sufficient quota
- [ ] Asana token has required permissions
- [ ] Logging configured for production
- [ ] Error monitoring set up (Sentry, etc.)
- [ ] Rate limiting configured if needed
- [ ] Database backup for conversation history (if needed)
- [ ] SSL/TLS enabled on production domain
- [ ] Scheduled task running at correct time (check timezone)

## Security Notes

- Never commit `.env` or actual credentials to git
- Use `.env.example` as template only
- Rotate API keys regularly
- Limit Asana token to required permissions only
- Monitor API usage for abuse
- Use environment variables for all secrets in production

## Support

For issues or questions, check:
- Twilio WhatsApp documentation
- Anthropic API documentation
- Asana API documentation
- Flask documentation

## License

Private - DreamFields/Jeeter
