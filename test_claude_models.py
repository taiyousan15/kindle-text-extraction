#!/usr/bin/env python3
"""Test available Claude models"""
import os
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

client = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))

# Try different model versions
models_to_test = [
    "claude-3-5-sonnet-20241022",
    "claude-3-5-sonnet-20240620",
    "claude-3-5-sonnet-latest",
    "claude-3-sonnet-20240229",
    "claude-3-opus-20240229",
    "claude-3-haiku-20240307",
]

print("Testing Claude API models...\n")

for model in models_to_test:
    try:
        message = client.messages.create(
            model=model,
            max_tokens=50,
            messages=[{"role": "user", "content": "Hi"}]
        )
        print(f"✅ {model} - WORKS")
    except Exception as e:
        print(f"❌ {model} - {str(e)[:80]}")
