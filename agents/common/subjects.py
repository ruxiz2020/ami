from subjects.domain_subject import DomainSubject
from subjects.person_subject import PersonSubject


def resolve_subjects_if_any(agent_name: str, text: str, ctx):
    """
    Language-agnostic subject resolution.

    Rules:
    1. If a clarification is pending, consume the answer verbatim.
    2. Do NOT infer or guess meanings.
    3. Free text inference is optional and disabled by default.
    """

    pending = getattr(ctx, "pending_subject", None)

    # --------------------------------------------------
    # 1. Consume explicit clarification answers
    # --------------------------------------------------
    if pending == "person":
        ctx.active_person = PersonSubject(
            subject_key="tmp_person",
            role="unspecified",
            descriptors={
                "user_provided": text.strip()
            },
            confidence=1.0,
            source="explicit",
        )
        ctx.pending_subject = None
        return

    if pending == "domain":
        ctx.active_domain = DomainSubject(
            domain=text.strip(),
            subdomain=text.strip(),
            confidence=1.0,
            source="explicit",
        )
        ctx.pending_subject = None
        return

    if ctx.pending_subject == "project":
        # treat user text as project name
        project_name = text.strip()
        if project_name:
            ctx.active_project = SimpleProject(descriptors=project_name)
            ctx.pending_subject = None
        return

    # --------------------------------------------------
    # 2. Optional soft inference (disabled by default)
    # --------------------------------------------------
    # Intentionally empty.
    # You may plug in LLM-based inference later.
    return


class SimpleProject:
    def __init__(self, descriptors: str):
        self.descriptors = descriptors
