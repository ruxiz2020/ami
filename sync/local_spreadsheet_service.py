# sync/local_spreadsheet_service.py

import csv
from pathlib import Path

def sync_rows_to_csv(rows, output_path: str):
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    if not rows:
        return {"status": "ok", "rows_written": 0}

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    return {
        "status": "ok",
        "rows_written": len(rows),
        "path": str(path),
    }
