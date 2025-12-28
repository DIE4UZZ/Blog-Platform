from typing import Any, Dict, Optional


def success_response(data: Optional[Any] = None, message: str = "ok") -> Dict[str, Any]:
    """Build a standardized success response.

    Args:
        data (Optional[Any]): Response payload data.
        message (str): Response message.

    Returns:
        Dict[str, Any]: Response dictionary with code/message/data.
    """

    return {
        "code": 0,
        "message": message,
        "data": data if data is not None else {},
    }


def error_response(code: int, message: str) -> Dict[str, Any]:
    """Build a standardized error response.

    Args:
        code (int): Error code.
        message (str): Error message.

    Returns:
        Dict[str, Any]: Response dictionary with code/message/data.
    """

    return {
        "code": code,
        "message": message,
        "data": {},
    }
