"""
Custom exceptions for the unified service
"""


class ServiceException(Exception):
    """Base exception for service errors"""
    def __init__(self, message: str, details: str = None):
        self.message = message
        self.details = details
        super().__init__(self.message)


class ClassificationException(ServiceException):
    """Exception for classification errors"""
    pass


class RAGException(ServiceException):
    """Exception for RAG service errors"""
    pass


class DesignerException(ServiceException):
    """Exception for designer service errors"""
    pass


class CodeSearchException(ServiceException):
    """Exception for code search errors"""
    pass


class DatabaseException(ServiceException):
    """Exception for database errors"""
    pass


class LLMException(ServiceException):
    """Exception for LLM errors"""
    pass


class ValidationException(ServiceException):
    """Exception for validation errors"""
    pass

