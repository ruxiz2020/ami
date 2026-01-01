## 🚀 Local Setup & Run

This project is designed to run **locally** using a Python virtual environment.

### 1️⃣ Create a virtual environment

From the project root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Run the app

```bash
python agents/ami/app.py

python -m agents.ami.app
```

### Example conversations


### Check data in db
```bash
cd /Users/XXX/ami
sqlite3 agents/ami/data/ami.db
.tables
SELECT * FROM observations;


```

### sync to gsheet
```bash
 curl -X POST http://127.0.0.1:5000/api/sync/google \
  -H "Content-Type: application/json" \
  -d '{"spreadsheet_id": "1me9XfhpnwMVE_8slPgADtsVKtP9xK-cfoZmdy0qmAUA"}'
```


