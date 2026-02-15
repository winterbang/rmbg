import requests
import os
import io

API_URL = "http://localhost:8000/remove-bg"
INPUT_FILE = "生气.png"
OUTPUT_FILE = "no_bg_生气.png"

def test_image():
    if not os.path.exists(INPUT_FILE):
        print(f"Error: {INPUT_FILE} not found.")
        return

    print(f"Processing {INPUT_FILE}...")
    with open(INPUT_FILE, "rb") as f:
        files = {"files": (INPUT_FILE, f, "image/png")}
        try:
            response = requests.post(API_URL, files=files)
            if response.status_code == 200:
                with open(OUTPUT_FILE, "wb") as out:
                    out.write(response.content)
                print(f"Success! Saved to {OUTPUT_FILE}")
            else:
                print(f"Failed: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"Request failed: {e}")

if __name__ == "__main__":
    test_image()
