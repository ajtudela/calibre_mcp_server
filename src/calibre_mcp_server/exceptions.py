"""
Custom exceptions for Calibre MCP Server.

This module defines custom exception classes that provide more specific
error handling and better error messages for the Calibre MCP Server.
"""


from typing import Optional


class CalibreServerError(Exception):
    """Base exception for Calibre MCP Server errors."""

    def __init__(
        self,
        message: str,
        details: Optional[str] = None
    ) -> None:
        """
        Initialize the exception with a message and optional details.

        Parameters
        ----------
        message : str
            The main error message.
        details : str, optional
            Additional error details, by default None.
        """
        self.message = message
        self.details = details
        super().__init__(self.message)


class DatabaseError(CalibreServerError):
    """Exception raised for database-related errors."""

    def __init__(
        self,
        message: str,
        operation: Optional[str] = None,
        details: Optional[str] = None
    ) -> None:
        """
        Initialize the database error.

        Parameters
        ----------
        message : str
            The main error message.
        operation : str, optional
            The database operation that failed, by default None.
        details : str, optional
            Additional error details, by default None.
        """
        self.operation = operation
        if operation:
            full_message = f"Database error during {operation}: {message}"
        else:
            full_message = f"Database error: {message}"
        super().__init__(full_message, details)


class ValidationError(CalibreServerError):
    """Exception raised for input validation errors."""

    def __init__(
        self,
        message: str,
        parameter: Optional[str] = None,
        value: Optional[str] = None
    ) -> None:
        """
        Initialize the validation error.

        Parameters
        ----------
        message : str
            The main error message.
        parameter : str, optional
            The parameter that failed validation, by default None.
        value : str, optional
            The invalid value, by default None.
        """
        self.parameter = parameter
        self.value = value
        if parameter:
            full_message = f"Validation error for '{parameter}': {message}"
        else:
            full_message = f"Validation error: {message}"
        super().__init__(full_message)


class NotFoundError(CalibreServerError):
    """Exception raised when requested resources are not found."""

    def __init__(
        self,
        resource_type: str,
        identifier: str,
        search_criteria: Optional[str] = None
    ) -> None:
        """
        Initialize the not found error.

        Parameters
        ----------
        resource_type : str
            The type of resource that was not found (e.g., 'book', 'author').
        identifier : str
            The identifier used to search for the resource.
        search_criteria : str, optional
            Additional search criteria, by default None.
        """
        self.resource_type = resource_type
        self.identifier = identifier
        self.search_criteria = search_criteria

        if search_criteria:
            message = (
                f"No {resource_type} found with {search_criteria}: "
                f"'{identifier}'"
            )
        else:
            message = f"No {resource_type} found: '{identifier}'"

        super().__init__(message)


class ConfigurationError(CalibreServerError):
    """Exception raised for configuration-related errors."""

    def __init__(
        self,
        message: str,
        setting: Optional[str] = None
    ) -> None:
        """
        Initialize the configuration error.

        Parameters
        ----------
        message : str
            The main error message.
        setting : str, optional
            The configuration setting that caused the error, by default None.
        """
        self.setting = setting
        if setting:
            full_message = f"Configuration error for '{setting}': {message}"
        else:
            full_message = f"Configuration error: {message}"
        super().__init__(full_message)
