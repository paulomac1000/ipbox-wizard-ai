"""Load the versioned oracle and schema as the package defaults."""

from __future__ import annotations

import sys

from . import oracle_v2 as _oracle_v2
from . import output_schema_v2 as _output_schema_v2

sys.modules[f"{__name__}.oracle"] = _oracle_v2
sys.modules[f"{__name__}.output_schema"] = _output_schema_v2
