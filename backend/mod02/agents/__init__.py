"""LangChain-powered agents.

- ``base.PersonaAgent``: shared persona voting logic.
- ``suresh``/``meena``/``arjun``/``kavya``/``ramesh``: the original five
  persona agents, each exposing ``build_agent(...)``.
- ``priya``/``vikram``/``fatima``/``dev_c``/``lakshmi``/``rohit``/``ananya``
  /``harish``/``zara``/``thomas``: ten additional persona agents.
- ``reviser.ReviserAgent``: rewrites failed posts from panel feedback.
- ``panel.VotingPanel``: orchestrates the persona agents and tallies votes.
"""

from backend.mod02.agents import (
    arjun, kavya, meena, ramesh, suresh,             # original five
    priya, vikram, fatima, dev_c, lakshmi,            # new batch 1
    rohit, ananya, harish, zara, thomas,              # new batch 2
)
from backend.mod02.agents.base import PersonaAgent
from backend.mod02.agents.panel import VotingPanel
from backend.mod02.agents.reviser import ReviserAgent

# Individual agent builders in canonical panel order.
AGENT_MODULES = [
    suresh, meena, arjun, kavya, ramesh,              # original five
    priya, vikram, fatima, dev_c, lakshmi,             # new batch 1
    rohit, ananya, harish, zara, thomas,               # new batch 2
]


def build_persona_agents(*, settings=None, cache=None):
    """Instantiate all fifteen persona agents."""

    return [m.build_agent(settings=settings, cache=cache) for m in AGENT_MODULES]


__all__ = [
    "PersonaAgent",
    "VotingPanel",
    "ReviserAgent",
    "AGENT_MODULES",
    "build_persona_agents",
]
