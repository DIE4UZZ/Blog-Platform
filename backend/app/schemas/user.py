from pydantic import BaseModel, EmailStr, Field, model_validator


class RegisterRequest(BaseModel):
    """用户注册请求体。"""

    username: str = Field(min_length=2, max_length=32)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, min_length=6, max_length=32)
    password: str = Field(min_length=6, max_length=72)

    @model_validator(mode="after")
    def validate_contact(self):
        """校验邮箱和手机号至少填写一项。"""

        if not self.email and not self.phone:
            raise ValueError("邮箱和手机号至少填写一项")
        return self


class LoginRequest(BaseModel):
    """用户登录请求体。"""

    account: str | None = Field(default=None, min_length=2, max_length=255)
    email: EmailStr | None = None
    username: str | None = Field(default=None, min_length=2, max_length=32)
    phone: str | None = Field(default=None, min_length=6, max_length=32)
    password: str = Field(min_length=6, max_length=72)

    @model_validator(mode="after")
    def validate_account(self):
        """校验至少提供一个登录标识。"""

        if not any([self.account, self.email, self.username, self.phone]):
            raise ValueError("请提供用户名、邮箱或手机号")
        return self


class PreferenceUpdateRequest(BaseModel):
    """更新偏好标签请求体。"""

    preference_tags: str
