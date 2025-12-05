import requests
import os
import sys
import subprocess
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# URL for the model wheel
MODEL_URL = "https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.7.1/en_core_web_sm-3.7.1-py3-none-any.whl"
FILENAME = "en_core_web_sm-3.7.1-py3-none-any.whl"

def download_file(url, filename):
    print(f"Downloading {filename}...")
    
    # Configure retry strategy
    retry_strategy = Retry(
        total=5,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    http = requests.Session()
    http.mount("https://", adapter)
    http.mount("http://", adapter)

    try:
        response = http.get(url, stream=True, timeout=60)
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        block_size = 1024 * 1024  # 1 MB
        wrote = 0
        
        with open(filename, 'wb') as f:
            for data in response.iter_content(block_size):
                wrote += len(data)
                f.write(data)
                if total_size > 0:
                    percent = wrote / total_size * 100
                    print(f"\rProgress: {percent:.1f}% ({wrote//1024} KB)", end='')
        print("\nDownload complete!")
        return True
    except Exception as e:
        print(f"\nError downloading: {e}")
        return False

def install_wheel(filename):
    print("Installing model...")
    try:
        # Use the pip from the current environment
        pip_cmd = [sys.executable, "-m", "pip", "install", filename]
        subprocess.check_call(pip_cmd)
        print("Installation successful!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Installation failed: {e}")
        return False

if __name__ == "__main__":
    if os.path.exists(FILENAME):
        print(f"File {FILENAME} already exists. Skipping download.")
        if install_wheel(FILENAME):
            print("✅ Model ready.")
            sys.exit(0)
    
    if download_file(MODEL_URL, FILENAME):
        if install_wheel(FILENAME):
            print("✅ Model setup complete.")
        else:
            print("❌ Installation failed.")
            sys.exit(1)
    else:
        print("❌ Download failed.")
        sys.exit(1)

