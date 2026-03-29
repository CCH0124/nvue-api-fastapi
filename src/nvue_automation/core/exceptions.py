class NVUEAPIError(Exception):
    """NVUE API 自定義異常"""

    def __init__(
        self,
        status_code: int,
        detail: str,
        title: str | None = None,
        error_type: str | None = None,
        response_body: dict | None = None,
        validation: dict | None = None,
    ):
        self.status_code = status_code
        self.detail = detail
        self.title = title
        self.error_type = error_type
        self.response_body = response_body or {}
        self.validation = validation or {}
        super().__init__(f"{status_code} - {detail}")

    def __str__(self):
        if self.title:
            return f"{self.status_code} {self.title}: {self.detail}"
        return f"{self.status_code}: {self.detail}"


class ConfigurationError(Exception):
    """Configuration related errors"""

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)
