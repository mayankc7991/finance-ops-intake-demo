import json
from typing import Any, Dict, List


def load_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def index_emails(emails: List[Dict]) -> Dict[str, Dict]:
    return {e["email_id"]: e for e in emails}
