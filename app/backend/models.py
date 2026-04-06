import uuid
from sqlalchemy import Column, String, Integer, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID
from app.backend.database import Base

class Messages(Base): 
    __tablename__ = "messages"
    message_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4())
    user_id = Column(Integer)
    message_type = Column(String)
    message_text = Column(String)
    timestamp = Column(TIMESTAMP)






