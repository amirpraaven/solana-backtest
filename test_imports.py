#!/usr/bin/env python3
"""Test if all required imports work"""

import sys
print(f"Python {sys.version}")

imports_to_test = [
    "fastapi",
    "uvicorn", 
    "pydantic",
    "asyncpg",
    "aioredis",
    "redis",
    "aiohttp",
    "httpx"
]

for module_name in imports_to_test:
    try:
        __import__(module_name)
        print(f"✓ {module_name}")
    except ImportError as e:
        print(f"✗ {module_name}: {e}")

print("\nTesting local imports...")
try:
    from src.web import app
    print("✓ src.web.app")
except Exception as e:
    print(f"✗ src.web.app: {e}")

print("\nDone!")