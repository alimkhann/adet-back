from pydantic import BaseModel, Field
from typing import Dict, Any

class ClerkWebhookPayload(BaseModel):
    data: Dict[str, Any]
    object: str
    type: str

class UserDeletedData(BaseModel):
    id: str
    deleted: bool