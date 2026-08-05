import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NOTICES = ROOT / "data" / "notices.json"
SCHOOLS = ROOT / "data" / "schools.json"
PENDING = ROOT / "data" / "pending-notices.json"

REQUIRED = {
    "id",
    "school",
    "college",
    "type",
    "title",
    "deadline",
    "sourceUrl",
    "tags",
    "lastCheckedAt",
    "verified",
}


def load(path):
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def check_deadline(value):
    datetime.fromisoformat(value)


def main():
    notices = load(NOTICES)
    schools = load(SCHOOLS)
    pending = load(PENDING)
    errors = []

    if not isinstance(notices, list):
        errors.append("data/notices.json must be a list")
    if not isinstance(schools, list):
        errors.append("data/schools.json must be a list")
    if not isinstance(pending, list):
        errors.append("data/pending-notices.json must be a list")

    seen_ids = set()
    for index, notice in enumerate(notices):
        missing = REQUIRED - set(notice)
        if missing:
            errors.append(f"notice[{index}] missing fields: {', '.join(sorted(missing))}")
        notice_id = notice.get("id")
        if notice_id in seen_ids:
            errors.append(f"duplicate id: {notice_id}")
        seen_ids.add(notice_id)
        try:
            check_deadline(notice.get("deadline", ""))
        except ValueError:
            errors.append(f"{notice_id} has invalid deadline")
        if not isinstance(notice.get("tags", []), list):
            errors.append(f"{notice_id} tags must be a list")

    for index, notice in enumerate(pending):
        required = (REQUIRED - {"deadline"}) | {"publishedAt", "sourceKind", "activityStatus"}
        missing = required - set(notice)
        if missing:
            errors.append(f"pending[{index}] missing fields: {', '.join(sorted(missing))}")
        notice_id = notice.get("id")
        if notice_id in seen_ids:
            errors.append(f"duplicate id across published/pending data: {notice_id}")
        seen_ids.add(notice_id)
        deadline = notice.get("deadline")
        if deadline:
            try:
                check_deadline(deadline)
            except ValueError:
                errors.append(f"{notice_id} has invalid pending deadline")
        if notice.get("verified") is not False:
            errors.append(f"{notice_id} pending record must have verified=false")
        try:
            datetime.fromisoformat(notice.get("publishedAt", ""))
        except ValueError:
            errors.append(f"{notice_id} has invalid publishedAt")

    if errors:
        print("Data validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print(f"Data OK: {len(notices)} notices, {len(pending)} pending, {len(schools)} target schools")
    return 0


if __name__ == "__main__":
    sys.exit(main())
