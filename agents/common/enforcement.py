def enforce_subjects(policy, ctx):
    """
    Enforce subject requirements based on policy.
    Returns (ok: bool, message: str | None)
    """
    # If we are already waiting for something, do NOT ask again
    if ctx.pending_subject is not None:
        return False, None

    if policy.require_person and ctx.active_person is None:
        ctx.pending_subject = "person"
        return False, "请先说明这条记录是关于哪一位的。"

    if policy.require_domain and ctx.active_domain is None:
        ctx.pending_subject = "domain"
        return False, "请先说明这条记录属于哪一类。"

    # project enforcement
    if policy.require_project and ctx.active_project is None:
        ctx.pending_subject = "project"
        return False, "这条记录属于哪个项目？请给出项目名称。"

    return True, None
