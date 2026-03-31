import logging
from twilio.rest import Client

logger = logging.getLogger(__name__)


def send_whatsapp_message(to_number, message, config):
    """Send WhatsApp message via Twilio."""
    try:
        account_sid = config.get('twilio_account_sid')
        auth_token = config.get('twilio_auth_token')
        from_number = config.get('twilio_phone')
        
        if not all([account_sid, auth_token, from_number]):
            logger.error("Missing Twilio configuration")
            return False
        
        client = Client(account_sid, auth_token)
        
        # Format phone numbers for Twilio
        to_whatsapp = f"whatsapp:{to_number}" if not to_number.startswith('whatsapp:') else to_number
        from_whatsapp = f"whatsapp:{from_number}" if not from_number.startswith('whatsapp:') else from_number
        
        message_obj = client.messages.create(
            body=message,
            from_=from_whatsapp,
            to=to_whatsapp
        )
        
        logger.info(f"WhatsApp message sent: {message_obj.sid}")
        return True
    
    except Exception as e:
        logger.error(f"Error sending WhatsApp message: {str(e)}")
        return False
