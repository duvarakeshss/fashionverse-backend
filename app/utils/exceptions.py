class UploadError(Exception):
    """Base exception for upload-related errors."""
    def __init__(self, detail: str, status_code: int = 400):
        self.detail = detail
        self.status_code = status_code
        super().__init__(detail)

class EmptyFileError(UploadError):
    def __init__(self, detail: str = "No file uploaded"):
        super().__init__(detail, status_code=400)

class UnsupportedFileTypeError(UploadError):
    def __init__(self, ext: str):
        super().__init__(f"Unsupported file type: {ext}", status_code=400)

class InvalidImageError(UploadError):
    def __init__(self, detail: str = "Invalid or corrupted image"):
        super().__init__(detail, status_code=400)

class FileTooLargeError(UploadError):
    def __init__(self, detail: str = "File exceeds 10MB limit"):
        super().__init__(detail, status_code=413)

class UserNotFoundError(UploadError):
    def __init__(self, detail: str = "User not found"):
        super().__init__(detail, status_code=404)
