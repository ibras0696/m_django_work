from pydantic import BaseModel

class DuePayload(BaseModel):
    user_id: int
    task_id: int
    title: str
    due_at: str | None = None