from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Categoria

router = APIRouter()


@router.get("/")
def listar_categorias(db: Session = Depends(get_db)):
    return db.query(Categoria).filter(Categoria.activa == True).all()  # noqa: E712
