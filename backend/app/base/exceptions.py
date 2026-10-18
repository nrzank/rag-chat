from typing import Any


class AppError(Exception):
    code = "internal_error"
    status_code = 500

    def __init__(
        self,
        message: str,
        *,
        params: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.params = params or {}
        self.context = context or {}


class NotFoundError(AppError):
    code = "not_found"
    status_code = 404


class ValidationError(AppError):
    code = "validation_error"
    status_code = 400


class DocumentNotFoundError(NotFoundError):
    code = "document_not_found"


class ConversationNotFoundError(NotFoundError):
    code = "conversation_not_found"


class UnsupportedFileTypeError(ValidationError):
    code = "unsupported_file_type"


class FileTooLargeError(ValidationError):
    code = "file_too_large"
    status_code = 413


class DocumentParsingError(AppError):
    code = "document_parsing_failed"
    status_code = 422
