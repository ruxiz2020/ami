# intelligence/templates.py

from pathlib import Path


def load_prompt_template(agent_name: str, report_type: str) -> str:
    """
    Loads a prompt template like:
    agents/ami/prompts/weekly_reflection.txt
    """
    path = Path("agents") / agent_name / "prompts" / f"{report_type}.txt"

    if not path.exists():
        raise FileNotFoundError(f"Missing prompt template: {path}")

    return path.read_text()
