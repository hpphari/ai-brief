#!/usr/bin/env python3
"""One-time Instagram login — saves session for future use."""
import instaloader, getpass, os

L = instaloader.Instaloader()
username = input("Instagram username: ").strip()
password = getpass.getpass("Instagram password: ")

try:
    L.login(username, password)
    L.save_session_to_file()
    # Also extract sessionid for .env
    sessionid = L.context._session.cookies.get("sessionid", domain=".instagram.com") or \
                L.context._session.cookies.get("sessionid")
    print(f"\nLogged in as @{username}")
    print(f"Session saved!")
    if sessionid:
        env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
        with open(env_path) as f:
            content = f.read()
        content = content.replace("IG_SESSION_ID=", f"IG_SESSION_ID={sessionid}")
        with open(env_path, "w") as f:
            f.write(content)
        print(f"IG_SESSION_ID added to .env automatically!")
except Exception as e:
    print(f"Login failed: {e}")
