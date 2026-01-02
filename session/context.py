class SessionContext:
    """
    Conversation-scoped state.
    Must persist across turns.
    """

    def __init__(self):
        # Resolved subjects
        self.active_domain = None
        self.active_person = None
        self.active_project = None

        # What clarification we are waiting for:
        # None | "person" | "domain"
        self.pending_subject = None

        # Collected content (what will actually be saved)
        self.collected_text = []

        # Optional control flag
        self.is_question_turn = False
