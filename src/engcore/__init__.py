"""Engineering AI Core distribution package.

Release 1 supports typed scientific and design APIs through their explicit
namespaces.  The pre-Release legacy optimizer remains importable from
``engcore.engine`` and ``engcore.models`` but is deliberately not re-exported
from the package root: its ``DesignSpace`` is not the typed Release 1 design
contract in :mod:`engcore.design`.
"""

from ._version import __version__

__all__ = ["__version__"]
