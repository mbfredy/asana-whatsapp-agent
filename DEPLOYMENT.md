# Deployment Checklist

Complete this checklist before deploying to production.

## Pre-Deployment

### Code Quality
- [ ] All Python files have proper error handling
- [ ] Logging is configured for production
- [ ] No hardcoded secrets or credentials
- [ ] All imports are in requirements.txt
- [ ] No TODO or FIXME comments in production code
- [ ] Code follows PEP 8 style guidelines

### Testing
- [ ] Run `python test_locally.py` - all tests pass
- [ ] Send test messages to WhatsApp - receive responses
- [ ] Verify morning digest formatting
- [ ] Test with various message types (questions, searches, etc.)
- [ ] Verify conversation history works correctly
- [ ] Check error handling with invalid Asana token

### Configuration
- [ ] `.env` file created with all required keys
- [ ] `config.json` not committed to git
- [ ] `.gitignore` configured properly
- [ ] All environment variables documented in `.env.example`

### Documentation
- [ ] README.md complete and accurate
- [ ] QUICKSTART.md tested and working
- [ ] Code comments added for complex logic
- [ ] API endpoint documentation in README

## Deployment Platform Setup

### Railway Deployment

1. [ ] GitHub account with code pushed
2. [ ] Railway account created at railway.app
3. [ ] Project created and connected to GitHub repo
4. [ ] Environment variables added:
   - [ ] TWILIO_ACCOUNT_SID
   - [ ] TWILIO_AUTH_TOKEN
   - [ ] TWILIO_PHONE
   - [ ] ANTHROPIC_API_KEY
   - [ ] ASANA_PAT
   - [ ] PORT (optional, defaults to 5000)
5. [ ] Procfile detected and deployed
6. [ ] Health endpoint responds (GET /)
7. [ ] Production URL obtained

### Render Deployment

1. [ ] GitHub account with code pushed
2. [ ] Render account created at render.com
3. [ ] Web Service created from GitHub repo
4. [ ] Build command set: `pip install -r requirements.txt`
5. [ ] Start command set: `gunicorn app:app`
6. [ ] Environment variables added (same as Railway)
7. [ ] Service deployed successfully
8. [ ] Health endpoint responds
9. [ ] Production URL obtained

## Twilio Configuration

1. [ ] Twilio Console accessed at console.twilio.com
2. [ ] WhatsApp Business Account setup complete (or Sandbox active)
3. [ ] Webhook URL updated to production domain
4. [ ] Webhook method set to POST
5. [ ] Test message sent to sandbox number
6. [ ] Response received within 3 seconds
7. [ ] WhatsApp Sandbox settings configured if using sandbox:
   - [ ] "When a message comes in" URL points to production
8. [ ] Production phone number configured if using Business Account

## API Keys & Tokens

- [ ] Anthropic API key has valid quota
- [ ] Asana PAT has access to user's workspace
- [ ] Asana PAT can read tasks and attachments
- [ ] Twilio credentials allow WhatsApp messages
- [ ] All API keys stored as environment variables
- [ ] No credentials in code repository

## Monitoring & Logging

1. [ ] Error monitoring configured (Sentry, DataDog, etc.)
2. [ ] Application logging level set to INFO for production
3. [ ] Log aggregation setup if needed (CloudWatch, Papertrail, etc.)
4. [ ] Health check monitoring configured
5. [ ] Alert system configured for errors
6. [ ] Uptime monitoring configured
7. [ ] APScheduler logs verified

## Security

1. [ ] SSL/TLS enabled on production domain
2. [ ] No sensitive data in logs
3. [ ] Rate limiting configured (if needed)
4. [ ] API key rotation schedule established
5. [ ] Only necessary permissions on Asana token
6. [ ] Webhook signature verification (if applicable)
7. [ ] CORS properly configured
8. [ ] Environment variables not exposed in error messages

## Performance

1. [ ] Flask app response time < 2 seconds
2. [ ] Database connections pooled (if using persistence)
3. [ ] API calls to Asana optimized
4. [ ] Conversation history pruned (last 20 messages)
5. [ ] No N+1 queries in Asana API calls
6. [ ] Memory usage monitored
7. [ ] Gunicorn workers configured appropriately

## Scheduled Tasks

1. [ ] APScheduler configured in app.py
2. [ ] Morning digest cron expression correct: `0 10 * * 0-4` (10 AM EST, weekdays)
3. [ ] Timezone set to US/Eastern
4. [ ] Test digest sent at scheduled time
5. [ ] Digest recipient phone configured
6. [ ] Scheduler logs show digest execution

## Post-Deployment

### Initial Verification
1. [ ] Production app running without errors
2. [ ] Health endpoint responds with 200
3. [ ] Send test WhatsApp message
4. [ ] Receive response within 3 seconds
5. [ ] Check production logs for errors
6. [ ] Verify conversation history working
7. [ ] Monitor first 24 hours for issues

### Day 1 Tasks
1. [ ] Test with various message types
2. [ ] Verify Asana task fetching works
3. [ ] Confirm morning digest timing
4. [ ] Check error messages are user-friendly
5. [ ] Monitor API usage across all services
6. [ ] Verify no rate limiting issues

### Week 1 Tasks
1. [ ] Review logs for patterns
2. [ ] Check API quota usage trends
3. [ ] Optimize Claude system prompt if needed
4. [ ] Verify digest content is helpful
5. [ ] Test error recovery paths
6. [ ] Performance baseline established

## Rollback Plan

If issues occur in production:

1. [ ] Previous working version tagged in git
2. [ ] Rollback procedure documented
3. [ ] Backup of config/data available
4. [ ] Twilio webhook can quickly revert URL
5. [ ] Communication plan for users established

## Maintenance Schedule

### Daily
- [ ] Monitor error logs
- [ ] Check API usage
- [ ] Verify scheduler running

### Weekly
- [ ] Review conversation patterns
- [ ] Check for API deprecations
- [ ] Verify all integrations working

### Monthly
- [ ] Rotate API keys
- [ ] Review and update dependencies
- [ ] Performance analysis
- [ ] User feedback review
- [ ] Security audit

## Contacts & Documentation

- [ ] Twilio support contact info saved
- [ ] Anthropic API support info saved
- [ ] Asana API documentation bookmarked
- [ ] Deployment platform support contact saved
- [ ] Incident escalation path defined
- [ ] On-call schedule if applicable

## Sign-Off

- [ ] Code review completed by: _________________
- [ ] Deployment approved by: _________________
- [ ] Deployment date/time: _________________
- [ ] Deployed by: _________________

---

## Notes

Use this section for deployment-specific notes or issues:

```
[Add deployment notes here]
```

---

Last Updated: 2024-01-15
