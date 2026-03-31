#!/usr/bin/env python3
"""
Local testing utility for the Asana WhatsApp Agent.
Run: python test_locally.py
"""

import os
import json
from asana_client import AsanaClient
from digest import generate_digest

def load_config():
    """Load configuration from config.json or environment."""
    config = {}
    config_file = os.path.join(os.path.dirname(__file__), 'config.json')
    
    if os.path.exists(config_file):
        with open(config_file, 'r') as f:
            config = json.load(f)
    
    config['asana_pat'] = os.getenv('ASANA_PAT', config.get('asana_pat'))
    config['anthropic_api_key'] = os.getenv('ANTHROPIC_API_KEY', config.get('anthropic_api_key'))
    
    return config

def test_asana_connection():
    """Test Asana API connection."""
    print("\n=== Testing Asana Connection ===")
    config = load_config()
    
    if not config.get('asana_pat'):
        print("ERROR: ASANA_PAT not set. Add to config.json or .env")
        return False
    
    try:
        client = AsanaClient(config['asana_pat'])
        user = client.get_user_me()
        
        print(f"✓ Connected to Asana")
        print(f"  User: {user.get('name')}")
        print(f"  Email: {user.get('email')}")
        
        # Test getting tasks
        tasks = client.get_my_tasks()
        print(f"✓ Retrieved {len(tasks)} tasks")
        
        if tasks:
            print("\n  Sample tasks:")
            for task in tasks[:3]:
                print(f"    - {task['name']}")
        
        return True
    
    except Exception as e:
        print(f"✗ Asana connection failed: {str(e)}")
        return False

def test_digest_generation():
    """Test digest generation."""
    print("\n=== Testing Digest Generation ===")
    config = load_config()
    
    if not config.get('asana_pat'):
        print("ERROR: ASANA_PAT not set")
        return False
    
    try:
        client = AsanaClient(config['asana_pat'])
        digest = generate_digest(client)
        
        print("✓ Digest generated successfully\n")
        print("--- DIGEST PREVIEW ---")
        print(digest)
        print("--- END PREVIEW ---\n")
        
        return True
    
    except Exception as e:
        print(f"✗ Digest generation failed: {str(e)}")
        return False

def test_anthropic_connection():
    """Test Anthropic API connection."""
    print("\n=== Testing Anthropic Connection ===")
    config = load_config()
    
    if not config.get('anthropic_api_key'):
        print("ERROR: ANTHROPIC_API_KEY not set. Add to config.json or .env")
        return False
    
    try:
        from anthropic import Anthropic
        client = Anthropic(api_key=config['anthropic_api_key'])
        
        response = client.messages.create(
            model="claude-sonnet-4-5-20250514",
            max_tokens=100,
            messages=[
                {"role": "user", "content": "Say 'Asana WhatsApp Agent is ready' in exactly 5 words."}
            ]
        )
        
        print("✓ Connected to Anthropic Claude API")
        print(f"  Response: {response.content[0].text}")
        
        return True
    
    except Exception as e:
        print(f"✗ Anthropic connection failed: {str(e)}")
        return False

def test_twilio_config():
    """Test Twilio configuration."""
    print("\n=== Testing Twilio Configuration ===")
    config = load_config()
    
    required_fields = ['twilio_account_sid', 'twilio_auth_token', 'twilio_phone']
    missing = [f for f in required_fields if not config.get(f)]
    
    if missing:
        print(f"ERROR: Missing Twilio config: {', '.join(missing)}")
        return False
    
    try:
        from twilio.rest import Client
        client = Client(config['twilio_account_sid'], config['twilio_auth_token'])
        account = client.api.accounts.get()
        
        print("✓ Connected to Twilio")
        print(f"  Account: {account.friendly_name}")
        print(f"  Phone: {config['twilio_phone']}")
        
        return True
    
    except Exception as e:
        print(f"✗ Twilio connection failed: {str(e)}")
        return False

def main():
    """Run all tests."""
    print("\n" + "="*50)
    print("  ASANA WHATSAPP AGENT - LOCAL TEST SUITE")
    print("="*50)
    
    tests = [
        ("Asana API", test_asana_connection),
        ("Anthropic Claude API", test_anthropic_connection),
        ("Twilio WhatsApp", test_twilio_config),
        ("Digest Generation", test_digest_generation),
    ]
    
    results = {}
    for name, test_func in tests:
        try:
            results[name] = test_func()
        except Exception as e:
            print(f"✗ Test failed with exception: {str(e)}")
            results[name] = False
    
    print("\n" + "="*50)
    print("  TEST RESULTS")
    print("="*50)
    
    for name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {name}")
    
    all_passed = all(results.values())
    
    print("="*50)
    if all_passed:
        print("\n✓ All tests passed! You're ready to deploy.")
        print("\nTo run the app:")
        print("  python app.py")
        print("\nTo test with Twilio:")
        print("  ngrok http 5000")
        print("  (then update Twilio webhook URL)")
    else:
        print("\n✗ Some tests failed. Fix errors above before deploying.")
    
    print()

if __name__ == '__main__':
    main()
