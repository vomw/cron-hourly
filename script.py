from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
import httpcloak
import os
import subprocess


class InputValueExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.subscription_url = None

    def handle_starttag(self, tag, attrs):
        if tag == "input":
            attrs_dict = dict(attrs)
            if attrs_dict.get("id") == "subscription":
                self.subscription_url = attrs_dict.get("value")


def main():
    secret_url = os.getenv("SECRET_URL")
    if not secret_url:
        raise ValueError("SECRET_URL environment variable not set")

    response = httpcloak.get(secret_url)
    response.raise_for_status()

    parser = InputValueExtractor()
    parser.feed(response.text)

    if not parser.subscription_url:
        raise ValueError("Could not find subscription URL in HTML")

    data_response = httpcloak.get(parser.subscription_url)
    data_response.raise_for_status()
    data_content = data_response.text

    latest_path = Path("latest")
    if latest_path.exists():
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        subprocess.run(["git", "mv", "latest", timestamp], check=True)

    latest_path.write_text(data_content)

    subprocess.run(["git", "add", "latest"], check=True)

    commit_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    commit_message = f"Auto-fetch: {commit_timestamp}"

    result = subprocess.run(
        ["git", "commit", "-m", commit_message], capture_output=True, text=True
    )

    if result.returncode == 0:
        subprocess.run(["git", "push"], check=True)


if __name__ == "__main__":
    main()
