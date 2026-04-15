from sqlalchemy import String, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from app.database import Base


class EmailProcesado(Base):
    __tablename__ = "emails_procesados"

    id: Mapped[int] = mapped_column(primary_key=True)
    gmail_message_id: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    remitente: Mapped[str] = mapped_column(String(200), nullable=False)
    asunto: Mapped[str] = mapped_column(String(500), nullable=False)
    # exitoso | ignorado | error
    resultado: Mapped[str] = mapped_column(String(20), nullable=False)
    error_detalle: Mapped[str | None] = mapped_column(Text, nullable=True)
    procesado_en: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    transacciones: Mapped[list["Transaccion"]] = relationship(back_populates="email_procesado")

    def __repr__(self) -> str:
        return f"<EmailProcesado {self.gmail_message_id} ({self.resultado})>"
