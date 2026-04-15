from sqlalchemy import String, Boolean, ForeignKey, DateTime, Numeric, Text, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from decimal import Decimal
from app.database import Base


class Transaccion(Base):
    __tablename__ = "transacciones"

    id: Mapped[int] = mapped_column(primary_key=True)
    cuenta_id: Mapped[int] = mapped_column(ForeignKey("cuentas.id"))
    categoria_id: Mapped[int | None] = mapped_column(ForeignKey("categorias.id"), nullable=True)
    email_procesado_id: Mapped[int | None] = mapped_column(ForeignKey("emails_procesados.id"), nullable=True)

    fecha: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    monto: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    # PEN | USD
    moneda: Mapped[str] = mapped_column(String(3), nullable=False)
    # cargo | abono
    tipo: Mapped[str] = mapped_column(String(10), nullable=False)
    descripcion: Mapped[str] = mapped_column(String(500), nullable=False)
    comercio: Mapped[str | None] = mapped_column(String(200), nullable=True)
    numero_operacion: Mapped[str | None] = mapped_column(String(50), nullable=True)
    categoria_manual: Mapped[bool] = mapped_column(Boolean, default=False)
    notas: Mapped[str | None] = mapped_column(Text, nullable=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    cuenta: Mapped["Cuenta"] = relationship(back_populates="transacciones")
    categoria: Mapped["Categoria"] = relationship(back_populates="transacciones")
    email_procesado: Mapped["EmailProcesado"] = relationship(back_populates="transacciones")

    def __repr__(self) -> str:
        return f"<Transaccion {self.tipo} {self.moneda} {self.monto} {self.fecha}>"
