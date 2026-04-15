from sqlalchemy import String, Boolean, ForeignKey, Date, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import date
from app.database import Base


class Cuenta(Base):
    __tablename__ = "cuentas"

    id: Mapped[int] = mapped_column(primary_key=True)
    institucion_id: Mapped[int] = mapped_column(ForeignKey("instituciones.id"))
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    # ahorros | credito | plazo_fijo | billetera
    tipo: Mapped[str] = mapped_column(String(20), nullable=False)
    # PEN | USD
    moneda: Mapped[str] = mapped_column(String(3), nullable=False)
    numero_cuenta: Mapped[str | None] = mapped_column(String(50), nullable=True)
    activa: Mapped[bool] = mapped_column(Boolean, default=True)
    fecha_alta: Mapped[date] = mapped_column(Date, nullable=False)
    fecha_baja: Mapped[date | None] = mapped_column(Date, nullable=True)
    notas: Mapped[str | None] = mapped_column(Text, nullable=True)

    institucion: Mapped["Institucion"] = relationship(back_populates="cuentas")
    transacciones: Mapped[list["Transaccion"]] = relationship(back_populates="cuenta")

    def __repr__(self) -> str:
        return f"<Cuenta {self.nombre} ({self.moneda})>"
