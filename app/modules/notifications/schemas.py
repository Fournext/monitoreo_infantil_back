from pydantic import BaseModel, Field

class NotificationSendRequest(BaseModel):
    token: str
    title: str
    body: str
    data: dict[str, str] = Field(default_factory=dict)
