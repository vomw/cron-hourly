from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
import base64
import httpcloak
import os
import subprocess
import sys


class InputValueExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.subscription_url = None

    def handle_starttag(self, tag, attrs):
        if tag == "input":
            attrs_dict = dict(attrs)
            if attrs_dict.get("id") == "subscription":
                self.subscription_url = attrs_dict.get("value")


def validate_environment():
    secret_url = os.getenv("SECRET_URL")
    if not secret_url:
        raise ValueError("SECRET_URL environment variable not set")
    return secret_url


def fetch_initial_page(url):
    try:
        response = httpcloak.get(url, preset="chrome-latest", timeout=60)
        response.raise_for_status()
        return response.text
    except Exception as e:
        raise RuntimeError(f"Failed to fetch initial page: {e}")


def extract_subscription_url(html_content):
    if not html_content or not html_content.strip():
        raise ValueError("Received empty HTML content")
    parser = InputValueExtractor()
    parser.feed(html_content)
    if not parser.subscription_url:
        raise ValueError("Could not find subscription URL in HTML (id='subscription')")
    if not parser.subscription_url.strip():
        raise ValueError("Subscription URL is empty")
    return parser.subscription_url


def fetch_data(url):
    try:
        response = httpcloak.get(url, preset="chrome-latest-ios", timeout=60)
        response.raise_for_status()
        return response.text
    except Exception as e:
        raise RuntimeError(f"Failed to fetch data from subscription URL: {e}")


def save_latest_file(content):
    latest_path = Path("latest")
    latest_path.write_text(content, encoding="utf-8")


def combine_with_existing_data(content):
    all_path = Path("all")
    if all_path.exists() and all_path.stat().st_size > 4:
        with open("all", "r") as f:
            encoded = f.read().strip()
        all_decoded = base64.b64decode(encoded).decode("utf-8")
        lines = set()
        for line in all_decoded.splitlines():
            if line.strip():
                lines.add(line)
        latest_decoded = base64.b64decode(content).decode("utf-8")
        for line in latest_decoded.splitlines():
            if line.strip():
                lines.add(line)
        combined = "\n".join(sorted(lines))
        encoded_output = base64.b64encode(combined.encode("utf-8")).decode("utf-8")
    else:
        encoded_output = content
    all_path.write_text(encoded_output, encoding="utf-8")


def commit_and_push():
    try:
        subprocess.run(["git", "add", "latest", "all"], check=True)
        result = subprocess.run(
            ["git", "diff", "--cached", "--quiet"], capture_output=True
        )
        if result.returncode == 0:
            print("No changes to commit")
            return False
        commit_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        commit_message = commit_timestamp
        subprocess.run(
            ["git", "commit", "-m", commit_message], check=True, capture_output=True
        )
        subprocess.run(["git", "push"], check=True)
        print(f"Successfully committed and pushed: {commit_message}")
        return True
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Git operation failed: {e}")


def main():
    try:
        print(f"Ver {httpcloak.version()} ")
        secret_url = validate_environment()
        print("Fetching initial page...")
        html_content = fetch_initial_page(secret_url)
        print("Extracting subscription URL...")
        subscription_url = extract_subscription_url(html_content)
        print("Downloading data...")
        data_content = fetch_data(subscription_url)
        print("Saving latest file...")
        save_latest_file(data_content)
        print("Adding to existing data...")
        combine_with_existing_data(data_content)
        print("Committing changes...")
        commit_and_push()
        print("Done!")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
