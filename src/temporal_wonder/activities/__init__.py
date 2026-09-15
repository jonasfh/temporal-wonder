"""Activities executing I/O and external service calls."""

from temporal_wonder.activities.legacy.logic_app import call_legacy_logic_app
from temporal_wonder.activities.native.native_step import execute_native_step

__all__ = [
    "call_legacy_logic_app",
    "execute_native_step",
]
