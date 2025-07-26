from pydantic import BaseModel, Field
from typing import Optional, Dict

class DeviceTokenRegister(BaseModel):
    device_token: str = Field(..., max_length=256)
    platform: str = Field("ios", max_length=16)
    app_version: Optional[str] = None
    system_version: Optional[str] = None

class DeviceTokenResponse(BaseModel):
    id: int
    device_token: str
    platform: str
    app_version: Optional[str]
    system_version: Optional[str]
    created_at: str

class NotificationSendRequest(BaseModel):
    user_id: int
    title: str
    body: str
    data: Optional[Dict[str, str]] = None
    category: Optional[str] = None