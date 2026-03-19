from pydantic import BaseModel # с pydantic легче, есть автовалидация


class RegisterReq(BaseModel):
    username: str
    password: str


class LoginReq(BaseModel):
    username: str
    password: str


class ShortenReq(BaseModel):
    original_url: str
    custom_alias: str | None = None
    expires_at: str | None = None


class UpdateReq(BaseModel):
    original_url: str
    #alias: 
