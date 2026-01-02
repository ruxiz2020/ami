from dataclasses import dataclass

@dataclass
class AgentSubjectPolicy:
    """
    Declarative requirements for an agent.
    """
    require_domain: bool = False
    require_person: bool = False
    require_project: bool = False
