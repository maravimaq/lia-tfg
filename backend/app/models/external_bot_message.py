from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import relationship

from app.db.session import Base


class ExternalBotMessage(Base):
    __tablename__ = "external_bot_messages"

    id_external_bot_message = Column(Integer, primary_key=True, index=True)
    session_id = Column(
        Integer,
        ForeignKey("external_bot_sessions.id_external_bot_session"),
        nullable=False,
        index=True,
    )
    role = Column(String, nullable=False)  # user | assistant | system
    content = Column(Text, nullable=False)
    metadata_json = Column(JSON, nullable=False, default=dict)
    fecha_creacion = Column(DateTime, nullable=False, default=datetime.utcnow)

    session = relationship("ExternalBotSession", back_populates="messages")
