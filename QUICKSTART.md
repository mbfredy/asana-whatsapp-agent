# Quick Start Guide

Get the Asana WhatsApp Agent running in 5 minutes.

## Step 1: Clone and Install

```bash
cd asana-whatsapp-agent
pip install -r requirements.txt
```

## Step 2: Get Your API Keys

**Anthropic (Claude):**
- Go to https://console.anthropic.com/account/keys
- Create new API key

**Asana:**
- Log into Asana
- Settings > Personal Access Tokens > Create
- Copy the token

**Twilio:**
- Go to https://www.twilio.com/console
- Copy Account SID from dashboard
- Go to Auth Tokens and copy your token
- Note your WhatsApp Sandbox number (or production number if set up)

## Step 3: Set Environment Variables

Create `.env` file:

```bash
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token_here
TWILIO_PHONE=+1415xxxxxxx
ANTHROPIC_API_KEY=sk-ant-v0-xxxxxxxxxxxxxxxxxxxxx
ASANA_PAT=0/xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

Or edit `config.json` with the same values.

## Step 4: Run Locally

```bash
python app.py
```

You'll see:
```
WARNING in app.run(): This is a development server...
 * Running on http://127.0.0.1:5000
```

## Step 5: Test with Ngrok

In another terminal:

```bash
ngrok http 5000
```

Copy the forwarding URL (e.g., `https://abc123.ngrok.io`).

## Step 6: Configure Twilio Webhook

1. Go to Twilio Console > Messaging > Settings > WhatsApp Sandbox Settings
2. Find "When a message comes in"
3. Paste your ngrok URL: `https://abc123.ngrok.io/webhook`
4. Save

## Step 7: Test

Send a WhatsApp message to your Twilio sandbox number:

```
What are my tasks today?
```

The bot should respond within 2-3 seconds.

## Debugging

Check the Flask logs in your terminal. Should see:
```
INFO:app:Received message from whatsapp:+1234567890: What are my tasks today?
INFO:app:Sent response to whatsapp:+1234567890
```

### Common Issues

**"No such module"**
- Run `pip install -r requirements.txt` again

**"401 Unauthorized"**
- Double-check API keys in `.env`
- Verify Asana token has access to your workspace

**"Webhook not receiving messages"**
- Verify ngrok URL in Twilio settings
- Check Twilio logs in console
- Ensure POST method selected in webhook

**"Claude API errors"**
- Verify `ANTHROPIC_API_KEY` is correct
- Check if you have API quota remaining

## Deploy to Production

### Railway (Recommended)

1. Push code to GitHub
2. Create account at railway.app
3. Create new project > GitHub repo
4. Add these environment variables:
   - TWILIO_ACCOUNT_SID
   - TWILIO_AUTH_TOKEN
   - TWILIO_PHONE
   - ANTHROPIC_API_KEY
   - ASANA_PAT

5. Railway auto-detects Procfile and deploys
6. Get your production URL from Railway dashboard
7. Update Twilio webhook: `https://your-railway-url.railway.app/webhook`

### Render

1. Push code to GitHub
2. Create account at render.com
3. Create new Web Service > GitHub repo
4. Set build command: `pip install -r requirements.txt`
5. Set start command: `gunicorn app:app`
6. Add same environment variables
7. Deploy
8. Update Twilio webhook with your Render URL

## Test the Health Endpoint

```bash
curl http://localhost:5000/health
```

Should return:
```json
{
  "status": "ok",
  "timestamp": "2024-01-15T10:30:45.123456",
  "service": "asana-whatsapp-agent"
}
```

## Morning Digest

The digest automatically runs at 10:00 AM EST every weekday. You'll receive:
- Tasks due today
- This week's tasks
- Tasks missing due dates
- Recent activity summary

To test digest generation:
```python
from digest import generate_digest
from asana_client import AsanaClient

client = AsanaClient('your_asana_pat')
digest = generate_digest(client)
print(digest)
```

## Next Steps

1. Customize the system prompt in `app.py` if needed
2. Add user preferences for digest timing
3. Implement database for persistent conversation history
4. Add logging/monitoring (Sentry, DataDog, etc.)
5. Set up automated testing
6. Configure rate limiting for production

## Support

- Flask docs: https://flask.palletsprojects.com/
- Twilio docs: https://www.twilio.com/docs/whatsapp/api
- Anthropic docs: https://docs.anthropic.com/
- Asana API: https://developers.asana.com/

Done! You're running an AI operations assistant.
