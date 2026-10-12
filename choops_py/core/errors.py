class ToolError(ValueError):
    """A stable error code plus a user-readable reason."""
    def __init__(self, code, detail):
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")
