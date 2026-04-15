from sqlalchemy import String, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Institucion(Base):
    __tablename__ = "instituciones"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    # Dominios de email separados por coma: "notificacionesbcp.com.pe,bcp.com.pe"
    # Vacío para instituciones sin email (ej: Efectivo)
    dominios_email: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    activa: Mapped[bool] = mapped_column(Boolean, default=True)

    cuentas: Mapped[list["Cuenta"]] = relationship(back_populates="institucion")

    def __repr__(self) -> str:
        return f"<Institucion {self.nombre}>"
