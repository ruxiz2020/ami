class CaretakerIntelligencePolicy:
    """
    Intelligence policy for Caretaker.

    This policy governs how medical history entries are summarized
    and reflected back to the user.

    Caretaker is strictly a record-keeping and recall assistant.
    It must not provide medical advice, diagnosis, interpretation,
    or recommendations.
    """

    # Human-readable name (used in logging / debugging)
    NAME = "caretaker"

    # Allowed reflection types
    ALLOWED_REPORT_TYPES = {
        "weekly_reflection",
        "medical_summary",
    }

    # Hard safety constraints (NEVER violate)
    FORBIDDEN_BEHAVIORS = [
        "diagnosing conditions",
        "interpreting symptoms or test results",
        "suggesting treatments or medications",
        "providing medical advice",
        "predicting outcomes or risks",
        "introducing external medical knowledge",
        "correcting the user's medical understanding",
    ]

    @staticmethod
    def build_prompt_context(entries):
        """
        Build a safe, factual context block from medical entries.

        Entries are expected to be already filtered
        (e.g., last 7 days, all history).
        """
        if not entries:
            return ""

        lines = []
        for e in entries:
            date = e.get("created_at") or e.get("date") or "Unknown date"
            text = e.get("text", "")
            lines.append(f"- [{date}] {text}")

        return "Recorded medical history entries:\n" + "\n".join(lines)

    @staticmethod
    def system_guidelines():
        """
        High-level behavioral constraints injected into the LLM prompt.
        """
        return """
You are generating a summary of recorded family medical history.

You must follow these rules strictly:

- Do NOT diagnose medical conditions.
- Do NOT interpret symptoms, test results, or outcomes.
- Do NOT recommend treatments, medications, or actions.
- Do NOT predict risks, progression, or prognosis.
- Do NOT introduce medical facts or explanations not stated by the user.
- Do NOT correct or challenge the user's understanding.

Your role is limited to organizing and restating
the recorded information accurately and neutrally.
""".strip()

    @staticmethod
    def output_guidelines():
        """
        Instructions on how the output should look.
        """
        return """
OUTPUT REQUIREMENTS:

- Use clear, factual language.
- Prefer chronological ordering when possible.
- Use bullet points for clarity.
- Do not add interpretations or conclusions.
- Keep the summary concise and neutral.
""".strip()
