
import yaml
import sqlite3
import json
from pathlib import Path

BASE_DIR = Path(__file__).parent
YAML_FILE = BASE_DIR / "data" / "alar.yml"
DB_FILE = BASE_DIR / "data" / "alar.db"


def read_value(parser, event):
    if isinstance(event, yaml.ScalarEvent):
        value = event.value

        if event.tag == "tag:yaml.org,2002:int":
            try:
                return int(value.replace("_", ""), 0)
            except ValueError:
                return value

        if event.tag == "tag:yaml.org,2002:bool":
            return value.lower() in ("true", "yes", "on")

        return value

    if isinstance(event, yaml.SequenceStartEvent):
        result = []
        while True:
            next_event = next(parser)
            if isinstance(next_event, yaml.SequenceEndEvent):
                break
            result.append(read_value(parser, next_event))
        return result

    if isinstance(event, yaml.MappingStartEvent):
        result = {}
        while True:
            key_event = next(parser)
            if isinstance(key_event, yaml.MappingEndEvent):
                break

            key = read_value(parser, key_event)
            value_event = next(parser)
            result[key] = read_value(parser, value_event)

        return result

    raise ValueError(f"Unexpected YAML event: {event}")



def entries_from_yaml(file):
    parser = iter(yaml.parse(file))

    while True:
        event = next(parser)
        if isinstance(event, yaml.DocumentStartEvent):
            break

    event = next(parser)

    if not isinstance(event, yaml.SequenceStartEvent):
        raise ValueError("Expected a YAML list at the top level.")

    while True:
        event = next(parser)

        if isinstance(event, yaml.SequenceEndEvent):
            break

        yield read_value(parser, event)


print("Starting streaming conversion...", flush=True)

if DB_FILE.exists():
    DB_FILE.unlink()

connection = sqlite3.connect(DB_FILE)

connection.execute("""
    CREATE TABLE alar (
        entry TEXT PRIMARY KEY,
        defs TEXT,
        phone TEXT
    )
""")

count = 0
batch = []

try:
    with open(YAML_FILE, "r", encoding="utf-8") as file:
        for item in entries_from_yaml(file):
            if not isinstance(item, dict) or not item.get("entry"):
                continue

            batch.append((
                item["entry"].strip(),
                json.dumps(item.get("defs", []), ensure_ascii=False),
                item.get("phone", "")
            ))

            if len(batch) >= 500:
                connection.executemany(
                    "INSERT OR REPLACE INTO alar VALUES (?, ?, ?)",
                    batch
                )
                count += len(batch)
                batch.clear()

                if count % 5000 == 0:
                    print(f"Processed {count} entries...", flush=True)

    if batch:
        connection.executemany(
            "INSERT OR REPLACE INTO alar VALUES (?, ?, ?)",
            batch
        )
        count += len(batch)

    connection.commit()

    print(f"\nConversion successful: {count} entries", flush=True)
    print(
        f"Database size: {DB_FILE.stat().st_size / (1024 * 1024):.2f} MB",
        flush=True
    )

except Exception:
    connection.rollback()
    raise

finally:
    connection.close()
