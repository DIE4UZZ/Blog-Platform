"""
schemas/user.py —— 用户相关请求/响应数据模式

使用 Pydantic 定义数据校验模型，FastAPI 自动完成：
  - 请求体反序列化与字段校验
  - 响应体序列化
  - OpenAPI 文档生成

模型说明：
  - RegisterRequest  : 注册接口请求体
  - LoginRequest     : 登录接口请求体
  - UpdatePreferenceRequest: 更新偏好标签请求体
"""

from typing import Optional

from pydantic import BaseModel, EmailStr, field_validator


class RegisterRequest(BaseModel):
    """用户注册请求体。

    校验规则：
      - username：必填，长度 2-64，不能包含空格
      - email 和 phone 至少填写一项（在路由层校验）
      - password：必填，长度 6-128

    Attributes:
        username (str): 用户名，2-64 字符，不含空格。
        email (Optional[str]): 邮箱地址，可为空。
        phone (Optional[str]): 手机号，可为空。
        password (str): 明文密码，6-128 字符（后端哈希后存储）。
    """

    username: str                       # 用户名，必填
    email: Optional[str] = None         # 邮箱，选填
    phone: Optional[str] = None         # 手机号，选填
    password: str                       # 密码，必填

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str) -> str:
        """校验用户名：去除首尾空格，检查长度范围（2-64）。"""
        value = value.strip()
        if len(value) < 2 or len(value) > 64:
            raise ValueError("用户名长度必须在 2-64 字符之间")
        return value

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        """校验密码：检查长度范围（6-128）。"""
        if len(value) < 6 or len(value) > 128:
            raise ValueError("密码长度必须在 6-128 字符之间")
        return value


class LoginRequest(BaseModel):
    """用户登录请求体。

    支持三种登录方式（在路由层判断优先级）：
      1. 用户名 + 密码
      2. 邮箱 + 密码
      3. 手机号 + 密码

    Attributes:
        account (Optional[str]): 通用账号字段（用户名/邮箱/手机号均可）。
        username (Optional[str]): 用户名（兼容旧版接口）。
        email (Optional[str]): 邮箱地址。
        phone (Optional[str]): 手机号。
        password (str): 明文密码。
    """

    account: Optional[str] = None      # 通用账号字段（前端统一传此字段）
    username: Optional[str] = None     # 用户名（兼容旧版）
    email: Optional[str] = None        # 邮箱
    phone: Optional[str] = None        # 手机号
    password: str                      # 密码，必填


class UpdatePreferenceRequest(BaseModel):
    """更新用户偏好标签请求体。

    Attributes:
        preference_tags (str): 偏好标签，逗号分隔字符串，例如 "Python,机器学习"。
            空字符串表示清空所有偏好标签。
    """

    preference_tags: str  # 偏好标签，逗号分隔


class UpdateProfileRequest(BaseModel):
    """更新用户个人资料请求体。

    所有字段均为可选，只更新传入的字段。

    Attributes:
        username (Optional[str]): 新用户名。
        email (Optional[str]): 新邮箱。
        phone (Optional[str]): 新手机号。
        bio (Optional[str]): 个人简介。
    """

    username: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    bio: Optional[str] = None


# 别名：兼容 routers/user.py 中的导入名称
PreferenceUpdateRequest = UpdatePreferenceRequest
