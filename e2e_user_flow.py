import requests
import sys
import time
import uuid

BASE_URL = "http://127.0.0.1:8000"

def get_unique_username():
    return f"user_{uuid.uuid4().hex[:8]}"

def test_flow():
    username = get_unique_username()
    email = f"{username}@example.com"
    password = "StrongPassword123!"
    
    print(f"--- Starting E2E User Flow Test for {username} ---")
    
    # 1. Register User
    print("\n1. Registering new user...")
    register_url = f"{BASE_URL}/api/auth/register"
    register_data = {
        "username": username,
        "email": email,
        "password": password
    }
    
    try:
        resp = requests.post(register_url, json=register_data)
        if resp.status_code == 201:
            print(f"✅ User registered successfully. ID: {resp.json().get('id')}")
            user_id = resp.json().get('id')
        else:
            print(f"❌ Registration failed: {resp.status_code} - {resp.text}")
            return
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print("Is the server running on port 8000?")
        return

    # 2. Login as Admin
    print("\n2. Logging in as Admin...")
    login_url = f"{BASE_URL}/api/auth/login"
    # Default admin credentials from init_db.py
    admin_data = {
        "username": "admin",
        "password": "admin123" 
    }
    
    admin_token = None
    try:
        resp = requests.post(login_url, json=admin_data)
        if resp.status_code == 200:
            admin_token = resp.json().get("access_token")
            print("✅ Admin login successful.")
        else:
            print(f"❌ Admin login failed: {resp.status_code} - {resp.text}")
            return
    except Exception as e:
        print(f"❌ Admin login error: {e}")
        return

    auth_headers = {"Authorization": f"Bearer {admin_token}"}

    # 3. Find the user in pending list (or just use the ID we got)
    # Verification step to ensure they show up in pending
    print("\n3. Verifying user is in pending list...")
    pending_url = f"{BASE_URL}/api/users/pending"
    try:
        resp = requests.get(pending_url, headers=auth_headers)
        if resp.status_code == 200:
            pending_users = resp.json()
            found = False
            for u in pending_users:
                if u['username'] == username:
                    found = True
                    print(f"✅ User {username} found in pending list.")
                    break
            if not found:
                print(f"⚠️ User {username} NOT found in pending list (maybe auto-approved or error?).")
        else:
            print(f"❌ Failed to get pending users: {resp.status_code} - {resp.text}")
    except Exception as e:
        print(f"❌ Error fetching pending users: {e}")

    # 4. Approve the user
    print(f"\n4. Approving user {user_id}...")
    approve_url = f"{BASE_URL}/api/users/{user_id}/approve"
    try:
        resp = requests.post(approve_url, headers=auth_headers)
        if resp.status_code == 200:
            print("✅ User approved successfully.")
        else:
            print(f"❌ Approval failed: {resp.status_code} - {resp.text}")
            return
    except Exception as e:
        print(f"❌ Error approving user: {e}")
        return

    # 5. Login as the new user
    print("\n5. Logging in as the new user...")
    user_login_data = {
        "username": username,
        "password": password
    }
    
    try:
        resp = requests.post(login_url, json=user_login_data)
        if resp.status_code == 200:
            print("✅ User login successful! Full flow complete.")
        else:
            print(f"❌ User login failed (even after approval): {resp.status_code} - {resp.text}")
    except Exception as e:
        print(f"❌ User login error: {e}")

if __name__ == "__main__":
    test_flow()
