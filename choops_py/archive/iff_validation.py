"""Name the failing archive and input role without guessing container repairs."""
from ..core.errors import ToolError
from ..formats.standard_iff import StandardIFF


def standard_iff(data, name, role):
    try:
        return StandardIFF(data)
    except ValueError as error:
        detail = f"{name} ({role}, magic={data[:4].hex() or 'empty'}): {error}"
        if isinstance(error, ToolError):
            raise ToolError(error.code, detail) from error
        raise ValueError(detail) from error
