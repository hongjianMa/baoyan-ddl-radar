"""Approve or reject crawler candidates from the command line."""

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PENDING_PATH = ROOT / "data" / "pending-notices.json"
NOTICES_PATH = ROOT / "data" / "notices.json"


def load(path):
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def save(path, value):
    with path.open("w", encoding="utf-8", newline="\n") as file:
        json.dump(value, file, ensure_ascii=False, indent=2)
        file.write("\n")


def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--list", action="store_true")
    group.add_argument("--approve", metavar="ID")
    group.add_argument("--reject", metavar="ID")
    parser.add_argument("--deadline", help="ISO time, required if the crawler did not find one")
    parser.add_argument("--college", help="Correct the college before publishing")
    args = parser.parse_args()

    pending = load(PENDING_PATH)
    if args.list:
        for item in pending:
            print(f'{item["id"]}\t{item["school"]}\t{item["deadline"] or "待补截止时间"}\t{item["title"]}')
        return 0

    target_id = args.approve or args.reject
    match = next((item for item in pending if item["id"] == target_id), None)
    if not match:
        raise SystemExit(f"Pending record not found: {target_id}")
    pending = [item for item in pending if item["id"] != target_id]

    if args.approve:
        deadline = args.deadline or match.get("deadline")
        if not deadline:
            raise SystemExit("Approval requires --deadline because no deadline was extracted")
        published = load(NOTICES_PATH)
        record = {key: value for key, value in match.items() if key not in {"discoveredAt", "reviewStatus", "confidence"}}
        record["deadline"] = deadline
        record["college"] = args.college or record["college"]
        record["verified"] = True
        record["tags"] = [tag for tag in record.get("tags", []) if tag != "自动发现"]
        published.append(record)
        save(NOTICES_PATH, published)
        print(f"Approved: {target_id}")
    else:
        print(f"Rejected: {target_id}")

    save(PENDING_PATH, pending)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
