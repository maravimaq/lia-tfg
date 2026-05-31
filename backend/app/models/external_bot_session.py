from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String, UniqueConstraint
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import relationship

from app.db.session import Base


class ExternalBotSession(Base):
    __tablename__ = "external_bot_sessions"
    __table_args__ = (
        UniqueConstraint(
            "channel",
            "external_chat_id",
            name="uq_external_bot_session_channel_chat",
        ),
    )

    id_external_bot_session = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id_usuario"), nullable=False, index=True)
    channel = Column(String, nullable=False, default="TELEGRAM", index=True)
    external_chat_id = Column(String, nullable=False, index=True)
    state = Column(String, nullable=False, default="idle")
    pending_action_json = Column(MutableDict.as_mutable(JSON), nullable=False, default=dict)
    fecha_creacion = Column(DateTime, nullable=False, default=datetime.utcnow)
    fecha_actualizacion = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    usuario = relationship("User")
    messages = relationship(
        "ExternalBotMessage",
        back_populates="session",
        cascade="all, delete-orphan",
    )
