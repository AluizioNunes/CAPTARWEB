import requests

def test_meta_auth_logic():
    url = "http://localhost:8000/api/integracoes/meta/test"
    
    print("1. Testing without any params (should fail with 400)")
    try:
        res = requests.get(url)
        print(f"Status: {res.status_code}")
        print(f"Response: {res.text}")
    except Exception as e:
        print(f"Error: {e}")

    print("\n2. Testing with query params (dummy token)")
    try:
        res = requests.get(url, params={
            "access_token": "dummy_token",
            "phone_number_id": "123456789",
            "base_url": "https://graph.facebook.com",
            "api_version": "v21.0"
        })
        print(f"Status: {res.status_code}")
        print(f"Response: {res.text}")
        if res.status_code == 400 and "Invalid OAuth" in res.text:
            print("SUCCESS: Endpoint attempted to use provided token.")
        elif res.status_code == 190: # OAuth error code from FB
             print("SUCCESS: Endpoint attempted to use provided token.")
        else:
             print("Check response content.")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_meta_auth_logic()
