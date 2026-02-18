
import requests
import base64
import os
from pathlib import Path

# Configuration
API_URL = "http://localhost:8000"
TEST_IMAGE_PATH = Path("test/test.png")
OUTPUT_DIR = Path("test/results")

def test_health():
    print(f"Testing Health Check ({API_URL}/health)...")
    try:
        response = requests.get(f"{API_URL}/health")
        if response.status_code == 200:
            print("✅ Health Check Passed:", response.json())
        else:
            print("❌ Health Check Failed:", response.status_code, response.text)
    except requests.exceptions.ConnectionError:
        print(f"❌ Could not connect to {API_URL}. Is the server running?")
        return False
    return True

def test_remove_bg():
    print(f"\nTesting Remove Background ({API_URL}/remove-bg)...")
    
    if not TEST_IMAGE_PATH.exists():
        print(f"❌ Test image not found at {TEST_IMAGE_PATH}")
        return

    OUTPUT_DIR.mkdir(exist_ok=True)
    
    files = {
        'files': ('test.png', open(TEST_IMAGE_PATH, 'rb'), 'image/png')
    }
    
    try:
        response = requests.post(f"{API_URL}/remove-bg", files=files)
        
        if response.status_code == 200:
            # Check if it's a zip (multiple files) or image
            content_type = response.headers.get('content-type')
            output_path = OUTPUT_DIR / "result_binary.png"
            
            if 'image' in content_type:
                with open(output_path, 'wb') as f:
                    f.write(response.content)
                print(f"✅ Remove BG Passed. Saved to {output_path}")
            else:
                print(f"✅ Remove BG Passed (ZIP). Content-Type: {content_type}")
        else:
            print("❌ Remove BG Failed:", response.status_code, response.text)
    except Exception as e:
        print(f"❌ Error during request: {e}")

def test_remove_bg_base64():
    print(f"\nTesting Remove Background Base64 ({API_URL}/remove-bg-base64)...")
    
    if not TEST_IMAGE_PATH.exists():
        print(f"❌ Test image not found at {TEST_IMAGE_PATH}")
        return

    # Encode image
    with open(TEST_IMAGE_PATH, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
    
    payload = {
        "image_base64": encoded_string
    }
    
    try:
        response = requests.post(f"{API_URL}/remove-bg-base64", json=payload)
        
        if response.status_code == 200:
            data = response.json()
            result_b64 = data.get("result")
            
            if result_b64:
                # Decode and save result
                image_data = base64.b64decode(result_b64)
                
                output_path = OUTPUT_DIR / "result_base64.png"
                with open(output_path, 'wb') as f:
                    f.write(image_data)
                print(f"✅ Remove BG Base64 Passed. Saved to {output_path}")
            else:
                print("❌ Remove BG Base64: No results in response")
        else:
            print("❌ Remove BG Base64 Failed:", response.status_code, response.text)
    except Exception as e:
        print(f"❌ Error during request: {e}")

if __name__ == "__main__":
    print("--- RMBG-2.0 API Test Script ---")
    if test_health():
        test_remove_bg()
        test_remove_bg_base64()
    else:
        print("\nPlease start the server first:")
        print("python3 run.py")
