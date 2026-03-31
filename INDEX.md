# Asana WhatsApp AI Agent - Complete File Index

## Quick Reference

| File | Purpose | Lines | Status |
|------|---------|-------|--------|
| **app.py** | Main Flask server | 258 | ✓ Production Ready |
| **asana_client.py** | Asana API wrapper | 155 | ✓ Production Ready |
| **digest.py** | Morning digest generator | 82 | ✓ Production Ready |
| **send_whatsapp.py** | Twilio message sender | 36 | ✓ Production Ready |
| **requirements.txt** | Python dependencies | 10 | ✓ Complete |
| **config.json** | Config template | 8 | ✓ Template |
| **.env.example** | Environment template | 18 | ✓ Template |
| **Procfile** | Deployment config | 2 | ✓ Ready |
| **.gitignore** | Git exclusions | 63 | ✓ Complete |
| **test_locally.py** | Integration tests | 185 | ✓ Utility |

## Documentation Files

| File | Purpose | Readers |
|------|---------|---------|
| **BUILD_SUMMARY.md** | Complete build overview | First-time users |
| **README.md** | Full documentation | Developers |
| **QUICKSTART.md** | 5-minute setup | New users |
| **DEPLOYMENT.md** | Pre-flight checklist | DevOps teams |
| **INDEX.md** | This file | Navigation |

## File Descriptions

### Core Application Files

#### app.py
**The main Flask application server.**
- Receives WhatsApp messages via POST /webhook
- Processes messages with Claude API
- Fetches Asana context (recent tasks, assigned tasks)
- Manages conversation history per user
- APScheduler for morning digest automation
- GET /health endpoint for monitoring
- Runs on gunicorn in production

**Key Functions:**
- `load_config()` - Load credentials from config.json or environment
- `get_asana_context()` - Fetch current Asana data for Claude context
- `get_conversation_history(user_phone)` - Retrieve user's message history
- `add_to_history()` - Store messages for conversation continuity
- `process_message_with_claude()` - Main message processing logic
- `format_for_whatsapp()` - Remove markdown, optimize for mobile
- `webhook()` - POST endpoint for incoming Twilio messages
- `health()` - GET endpoint for health checks
- `send_morning_digest()` - Generate and send daily digest
- `init_scheduler()` - Initialize APScheduler for cron jobs

**Dependencies:**
- Flask, Anthropic, Twilio, APScheduler, requests

#### asana_client.py
**Asana REST API client wrapper.**
- All API calls use Personal Access Token (PAT) authentication
- Handles pagination, error handling, timeouts
- Returns Asana task data formatted for Claude

**Key Methods:**
- `get_my_tasks()` - Get incomplete tasks assigned to user
- `get_task_details(task_id)` - Full task with descriptions, subtasks
- `get_task_attachments(task_id)` - File attachments for a task
- `get_recent_tasks(days=7)` - Recently modified tasks
- `search_tasks(query)` - Text search across tasks
- `get_user_me()` - Current user information

**Error Handling:**
- Logs all errors, returns empty lists on failure
- Graceful fallbacks if API unavailable

#### digest.py
**Morning digest generator.**
- Pulls all Asana task data
- Prioritizes: due today > this week > no due date
- Formats for WhatsApp (plain text, mobile-optimized)
- Called by scheduler at 10 AM EST on weekdays

**Key Function:**
- `generate_digest(asana_client)` - Main digest generation
  - Returns formatted string with task summary
  - Handles errors gracefully

#### send_whatsapp.py
**Twilio WhatsApp message sender.**
- Simple wrapper around Twilio SDK
- Handles phone number formatting
- Returns success/failure boolean

**Key Function:**
- `send_whatsapp_message(to_number, message, config)` - Send WhatsApp

### Configuration Files

#### config.json
**Local configuration template.**
- Contains Twilio credentials, API keys, PAT
- Overridden by environment variables in production
- Should NOT be committed to git (in .gitignore)

**Fields:**
```json
{
  "twilio_account_sid": "string",
  "twilio_auth_token": "string",
  "twilio_phone": "+1234567890",
  "anthropic_api_key": "string",
  "asana_pat": "string"
}
```

#### .env.example
**Environment variable template for production.**
- Copy to `.env` for local development
- Set all values before running
- Used by Railway, Render, Docker, etc.

**All Variables:**
- TWILIO_ACCOUNT_SID
- TWILIO_AUTH_TOKEN
- TWILIO_PHONE
- ANTHROPIC_API_KEY
- ASANA_PAT
- PORT (optional)
- FLASK_ENV
- DIGEST_RECIPIENT_PHONE

#### requirements.txt
**Python package dependencies with versions.**
- Flask 3.0.0 - Web framework
- Twilio 8.10.0 - WhatsApp messaging
- anthropic 0.25.9 - Claude API
- APScheduler 3.10.4 - Scheduled tasks
- Gunicorn 21.2.0 - Production WSGI server
- requests 2.31.0 - HTTP library
- python-dotenv 1.0.0 - .env file support
- pytz 2024.1 - Timezone support

#### Procfile
**Deployment configuration for Heroku-like platforms.**
- Used by Railway, Render, Heroku
- Tells platform how to run the app
- Command: `web: gunicorn app:app`

#### .gitignore
**Git exclusion rules.**
- Excludes: .env, config.json, __pycache__, venv
- Excludes IDE settings, logs, databases
- Ensures credentials never committed

### Deployment & Utility Files

#### test_locally.py
**Local integration testing utility.**
- Verify Asana API connection
- Verify Anthropic API connection
- Verify Twilio configuration
- Test digest generation
- Run: `python test_locally.py`

**Outputs:**
- Connection status for each service
- Sample data from Asana
- Test digest preview

### Documentation Files

#### BUILD_SUMMARY.md
**Overview of the complete build.**
- File inventory
- Feature summary
- Architecture diagram
- Getting started
- Next steps

**Read This:** First time understanding the project

#### README.md
**Complete reference documentation.**
- Setup instructions
- Features overview
- Credential retrieval (step-by-step)
- Local testing with ngrok
- Deployment guides (Railway, Render)
- Architecture explanation
- Troubleshooting
- API endpoints
- Security notes
- Production checklist

**Read This:** Before deploying or troubleshooting

#### QUICKSTART.md
**Fast 5-minute setup guide.**
- Install dependencies
- Get API keys
- Set up .env
- Run locally
- Test with ngrok
- Configure Twilio
- Debug common issues

**Read This:** First-time local setup

#### DEPLOYMENT.md
**Pre-deployment verification checklist.**
- Code quality checks
- Testing verification
- Configuration checks
- Platform-specific setup (Railway, Render)
- Twilio configuration
- Security verification
- Performance checklist
- Post-deployment tasks
- Maintenance schedule

**Read This:** Before going to production

#### INDEX.md
**This file.** Navigation and file reference.

## Getting Started Flowchart

```
Start Here
    ↓
Read BUILD_SUMMARY.md (overview)
    ↓
Follow QUICKSTART.md (local setup)
    ↓
Run test_locally.py (verify integrations)
    ↓
Send test WhatsApp message
    ↓
Review README.md (understand fully)
    ↓
Ready for production?
    ↓ YES
Use DEPLOYMENT.md checklist
    ↓
Deploy to Railway or Render
    ↓
Verify with test messages
    ↓
Production running!
```

## Common Tasks

### I want to run locally
1. pip install -r requirements.txt
2. Copy .env.example to .env
3. python test_locally.py
4. python app.py
5. ngrok http 5000
6. Update Twilio webhook

### I want to deploy
1. Push to GitHub
2. Create project on Railway.app or Render.com
3. Add environment variables
4. Deploy (auto-detected via Procfile)
5. Update Twilio webhook to production URL
6. Test with WhatsApp message

### I want to understand the code
1. Read BUILD_SUMMARY.md (overview)
2. Read app.py (main logic)
3. Read asana_client.py (Asana integration)
4. Read digest.py (digest logic)
5. Read README.md (full docs)

### I'm troubleshooting
1. Check README.md troubleshooting section
2. Run test_locally.py
3. Check Flask logs
4. Verify .env variables
5. Check Twilio console

### I want to customize
1. Edit system prompt in app.py (around line 70)
2. Edit digest format in digest.py
3. Edit Asana client methods in asana_client.py
4. Edit response formatting in app.py

## File Statistics

**Total Files:** 14
**Total Lines of Code:** ~1,200
**Total Documentation:** ~1,000 lines
**Total Lines:** ~2,200

**Breakdown:**
- Python Code: ~710 lines
- Configuration: ~38 lines
- Documentation: ~1,172 lines
- Other: ~280 lines

## Production Deployment Checklist

Before deploying, verify:
- [ ] All environment variables set
- [ ] test_locally.py passes
- [ ] README.md reviewed
- [ ] DEPLOYMENT.md checklist completed
- [ ] Twilio webhook configured
- [ ] Code pushed to GitHub
- [ ] Platform account created (Railway/Render)
- [ ] Health endpoint tested
- [ ] Test message sent to WhatsApp

## Support Resources

- Flask: https://flask.palletsprojects.com/
- Twilio: https://www.twilio.com/docs/whatsapp/api
- Anthropic: https://docs.anthropic.com/
- Asana: https://developers.asana.com/
- Railway: https://docs.railway.app/
- Render: https://render.com/docs

## Key Concepts

**Webhook:** URL where Twilio sends incoming WhatsApp messages
**PAT:** Personal Access Token for Asana API authentication
**Cron:** Scheduled job expression (morning digest timing)
**Context:** Asana data provided to Claude with each message
**History:** Last 20 messages per user for conversation continuity
**Digest:** Automated morning task summary sent at 10 AM EST

---

**Total Build Time:** Complete and ready for deployment
**Last Updated:** January 2024
**Status:** Production Ready
