"""Legacy activities delegating work to external Azure Logic Apps via HTTP."""

from temporal_wonder.activities.legacy.logic_app import call_legacy_logic_app

__all__ = ["call_legacy_logic_app"]
