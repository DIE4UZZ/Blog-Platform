from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    """Request body for user registration.

    Attributes:
        email (EmailStr): User email address.
        password (str): Plain-text password.
    """

    email: EmailStr
    password: str = Field(min_length=6)


class LoginRequest(BaseModel):
    """Request body for user login.

    Attributes:
        email (EmailStr): User email address.
        password (str): Plain-text password.
    """

    email: EmailStr
    password: str = Field(min_length=6)


class PreferenceUpdateRequest(BaseModel):
    """Request body for updating user preference tags.

    Attributes:
        preference_tags (str): Comma-separated preference tags.
    """

    preference_tags: str
