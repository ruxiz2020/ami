from pathlib import Path

BASE_DIR = Path(__file__).parent

def load_system_prompt():
    return (BASE_DIR / "system_prompt.txt").read_text()

def load_developer_prompt():
    return (BASE_DIR / "developer_prompt.txt").read_text()
