from sqlalchemy import Column, Integer, String, Boolean, DateTime
from datetime import datetime
from app.database import Base


class Usuario(Base):
    __tablename__ = "usuarios"

    id           = Column(Integer, primary_key=True, index=True)
    username     = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    activo       = Column(Boolean, default=True)
    creado_en    = Column(DateTime, default=datetime.utcnow)
