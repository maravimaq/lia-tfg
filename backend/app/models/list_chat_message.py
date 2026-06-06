from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import relationship

from app.db.session import Base


class ListChatMessage(Base):
    __tablename__ = "list_chat_messages"

    id_chat_message = Column(Integer, primary_key=True, index=True)
    lista_id = Column(Integer, ForeignKey("listas_compra.id_lista"), nullable=False, index=True)
    usuario_id = Column(Integer, ForeignKey("users.id_usuario"), nullable=False, index=True)
    role = Column(String(20), nullable=False)  # user | assistant
    content = Column(Text, nullable=False)
    intent = Column(String(80), nullable=True)
    suggestions_json = Column(JSON, nullable=False, default=list)
    context_summary_json = Column(JSON, nullable=False, default=dict)
    fecha_creacion = Column(DateTime, nullable=False, default=datetime.utcnow)

    lista = relationship("ListaCompra")
    usuario = relationship("User")
