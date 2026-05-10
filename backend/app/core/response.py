"""
core/response.py —— 统一响应体构造工具

所有 API 接口均使用本模块的函数构造响应，保证前端收到的 JSON 格式一致：
  {
    "code":    0,          # 0 表示成功，非 0 表示业务错误
    "message": "ok",       # 人类可读的提示信息
    "data":    { ... }     # 业务数据，失败时为空对象 {}
  }
"""

from typing import Any, Dict, Optional


def success_response(data: Optional[Any] = None, message: str = "ok") -> Dict[str, Any]:
    """构造标准成功响应体。

    Args:
        data (Optional[Any]): 要返回给前端的业务数据，
            若为 None 则自动替换为空字典 {}，避免前端收到 null。
        message (str): 成功提示信息，默认 "ok"。

    Returns:
        Dict[str, Any]: 包含 code/message/data 三个字段的字典。

    示例：
        success_response({"user_id": 1}, message="注册成功")
        # → {"code": 0, "message": "注册成功", "data": {"user_id": 1}}
    """
    return {
        "code": 0,                              # 0 代表业务成功
        "message": message,
        "data": data if data is not None else {},  # None 转为空对象
    }


def error_response(code: int, message: str) -> Dict[str, Any]:
    """构造标准错误响应体。

    业务错误码约定（与 main.py 异常处理器对应）：
      4001 → 通用客户端错误
      4002 → 未登录 / Token 失效
      4003 → 权限不足
      4004 → 资源不存在
      5000 → 服务器内部错误

    Args:
        code (int): 业务错误码（非 0）。
        message (str): 错误描述信息，将直接展示给前端。

    Returns:
        Dict[str, Any]: 包含 code/message/data 三个字段的字典，data 固定为 {}。

    示例：
        error_response(4004, "文章不存在")
        # → {"code": 4004, "message": "文章不存在", "data": {}}
    """
    return {
        "code": code,
        "message": message,
        "data": {},   # 错误时 data 固定为空对象
    }
