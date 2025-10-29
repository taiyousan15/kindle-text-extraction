"""
Simple test script for JWT authentication system
"""
import requests
import json

BASE_URL = "http://localhost:8000"

def test_authentication():
    print("=" * 60)
    print("JWT Authentication System Test")
    print("=" * 60)

    # Test 1: Register a new user
    print("\n1. Testing User Registration...")
    register_data = {
        "email": "testuser@example.com",
        "password": "securepassword123",
        "name": "Test User"
    }

    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/register",
            json=register_data
        )
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")

        if response.status_code == 201:
            print("✅ User registration successful!")
        elif response.status_code == 400 and "already exists" in response.text:
            print("ℹ️  User already exists, proceeding with login test...")
        else:
            print(f"❌ Registration failed: {response.text}")
    except Exception as e:
        print(f"❌ Error: {e}")
        return

    # Test 2: Login
    print("\n2. Testing User Login...")
    login_data = {
        "email": "testuser@example.com",
        "password": "securepassword123"
    }

    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json=login_data
        )
        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print("✅ Login successful!")
            print(f"Access Token: {data['access_token'][:50]}...")
            print(f"Refresh Token: {data['refresh_token'][:50]}...")
            print(f"Token Type: {data['token_type']}")
            print(f"Expires In: {data['expires_in']} seconds")
            print(f"User: {data['user']['name']} ({data['user']['email']})")

            access_token = data['access_token']
            refresh_token = data['refresh_token']
        else:
            print(f"❌ Login failed: {response.text}")
            return
    except Exception as e:
        print(f"❌ Error: {e}")
        return

    # Test 3: Access protected endpoint (Get current user)
    print("\n3. Testing Protected Endpoint (/api/v1/auth/me)...")
    try:
        headers = {
            "Authorization": f"Bearer {access_token}"
        }
        response = requests.get(
            f"{BASE_URL}/api/v1/auth/me",
            headers=headers
        )
        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print("✅ Protected endpoint access successful!")
            print(f"User ID: {data['id']}")
            print(f"Email: {data['email']}")
            print(f"Name: {data['name']}")
            print(f"Is Active: {data['is_active']}")
        else:
            print(f"❌ Failed to access protected endpoint: {response.text}")
    except Exception as e:
        print(f"❌ Error: {e}")

    # Test 4: Access protected endpoint without token
    print("\n4. Testing Protected Endpoint Without Token...")
    try:
        response = requests.get(f"{BASE_URL}/api/v1/auth/me")
        print(f"Status Code: {response.status_code}")

        if response.status_code == 401 or response.status_code == 403:
            print("✅ Correctly blocked access without authentication!")
            print(f"Error: {response.json()}")
        else:
            print(f"❌ Unexpected response: {response.text}")
    except Exception as e:
        print(f"❌ Error: {e}")

    # Test 5: Refresh token
    print("\n5. Testing Token Refresh...")
    try:
        refresh_data = {
            "refresh_token": refresh_token
        }
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/refresh",
            json=refresh_data
        )
        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print("✅ Token refresh successful!")
            print(f"New Access Token: {data['access_token'][:50]}...")
            print(f"New Refresh Token: {data['refresh_token'][:50]}...")
        else:
            print(f"❌ Token refresh failed: {response.text}")
    except Exception as e:
        print(f"❌ Error: {e}")

    # Test 6: Test OCR endpoint with authentication
    print("\n6. Testing OCR Endpoint With Authentication...")
    try:
        headers = {
            "Authorization": f"Bearer {access_token}"
        }
        # We won't actually upload a file, just check if the endpoint requires auth
        response = requests.post(
            f"{BASE_URL}/api/v1/ocr/upload",
            headers=headers
        )
        print(f"Status Code: {response.status_code}")

        if response.status_code == 422:  # Missing file parameter
            print("✅ OCR endpoint accessible with auth (422 expected - missing file)")
        elif response.status_code == 401:
            print("❌ OCR endpoint still requires authentication correctly")
        else:
            print(f"ℹ️  Response: {response.status_code} - {response.text[:100]}")
    except Exception as e:
        print(f"❌ Error: {e}")

    # Test 7: Test OCR endpoint without authentication
    print("\n7. Testing OCR Endpoint Without Authentication...")
    try:
        response = requests.post(f"{BASE_URL}/api/v1/ocr/upload")
        print(f"Status Code: {response.status_code}")

        if response.status_code == 401 or response.status_code == 403:
            print("✅ OCR endpoint correctly blocked without authentication!")
        else:
            print(f"❌ Unexpected response: {response.status_code} - {response.text[:100]}")
    except Exception as e:
        print(f"❌ Error: {e}")

    print("\n" + "=" * 60)
    print("Test Complete!")
    print("=" * 60)


if __name__ == "__main__":
    test_authentication()
