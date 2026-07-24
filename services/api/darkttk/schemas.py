from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from .models import Role


class RegisterRequest(BaseModel):
    email: EmailStr
    display_name: str = Field(min_length=2, max_length=120)
    password: str = Field(min_length=12, max_length=128)
    organization_name: str = Field(min_length=2, max_length=120)

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, value: str) -> str:
        classes = (
            any(char.islower() for char in value),
            any(char.isupper() for char in value),
            any(char.isdigit() for char in value),
            any(not char.isalnum() for char in value),
        )
        if sum(classes) < 3:
            raise ValueError("A senha deve combinar ao menos três tipos de caracteres.")
        return value


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)
    organization_id: str | None = None
    mfa_code: str | None = Field(default=None, min_length=6, max_length=32)


class WorkspaceExchangeRequest(BaseModel):
    email: EmailStr
    display_name: str = Field(min_length=2, max_length=120)


class PasswordRecoveryRequest(BaseModel):
    email: EmailStr


class PasswordRecoveryResponse(BaseModel):
    accepted: bool = True
    delivery_mode: str
    development_token: str | None = None


class PasswordRecoveryConfirm(BaseModel):
    token: str = Field(min_length=32, max_length=256)
    new_password: str = Field(min_length=12, max_length=128)

    @field_validator("new_password")
    @classmethod
    def validate_new_password_strength(cls, value: str) -> str:
        return RegisterRequest.validate_password_strength(value)


class MfaCodeRequest(BaseModel):
    code: str = Field(min_length=6, max_length=32)


class MfaSetupResponse(BaseModel):
    secret: str
    provisioning_uri: str


class MfaConfirmResponse(BaseModel):
    enabled: bool
    recovery_codes: list[str]


class MfaStatusResponse(BaseModel):
    enabled: bool
    confirmed_at: datetime | None
    recovery_codes_remaining: int


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=32)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class OrganizationSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    slug: str
    role: str


class UserResponse(BaseModel):
    id: str
    email: EmailStr
    display_name: str
    role: str
    organization: OrganizationSummary


class InviteMemberRequest(BaseModel):
    email: EmailStr
    display_name: str = Field(min_length=2, max_length=120)
    role: Role


class UpdateMemberRoleRequest(BaseModel):
    role: Role


class MemberResponse(BaseModel):
    id: str
    user_id: str
    email: EmailStr
    display_name: str
    role: str
    status: str
    created_at: datetime
