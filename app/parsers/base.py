from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from abc import ABC, abstractmethod
import re
from bs4 import BeautifulSoup


@dataclass
class EmailData:
    message_id: str
    remitente: str
    asunto: str
    cuerpo_html: str
    cuerpo_texto: str
    fecha_recibido: datetime


@dataclass
class TransaccionParseada:
    cuenta_nombre: str        # Nombre de la cuenta en el sistema
    fecha: datetime
    monto: Decimal
    moneda: str               # PEN | USD
    tipo: str                 # cargo | abono
    descripcion: str
    comercio: str | None = None
    numero_operacion: str | None = None


class BaseParser(ABC):
    """Clase base para todos los parsers de email bancario."""

    # Sujetos de email que deben IGNORARSE (configuración, marketing, etc.)
    ASUNTOS_IGNORAR: list[str] = []

    @property
    @abstractmethod
    def dominios(self) -> list[str]:
        """Lista de dominios de email que este parser maneja."""
        ...

    @abstractmethod
    def puede_parsear(self, email: EmailData) -> bool:
        """Retorna True si este parser puede manejar el email."""
        ...

    @abstractmethod
    def parsear(self, email: EmailData) -> list[TransaccionParseada]:
        """Extrae transacciones del email. Retorna lista vacía si no hay transacciones."""
        ...

    # ---- Helpers compartidos ----

    def _es_remitente_valido(self, remitente: str) -> bool:
        remitente_lower = remitente.lower()
        return any(dominio in remitente_lower for dominio in self.dominios)

    def _es_asunto_ignorable(self, asunto: str) -> bool:
        asunto_lower = asunto.lower()
        return any(ignorar.lower() in asunto_lower for ignorar in self.ASUNTOS_IGNORAR)

    @staticmethod
    def _html_a_texto(html: str) -> str:
        soup = BeautifulSoup(html, "html.parser")
        texto = soup.get_text(separator=" ", strip=True)
        texto = re.sub(r"[\u200b\u200c\u200d\ufeff]", "", texto)
        return re.sub(r"\s+", " ", texto).strip()

    @staticmethod
    def _extraer_monto(texto: str, patrones: list[str]) -> Decimal | None:
        """
        Busca un monto monetario en el texto usando los patrones dados.
        Los patrones deben tener un grupo de captura para el número.
        Ej: r'Monto total S/' + r'\s*([\d,\.]+)'
        """
        for patron in patrones:
            m = re.search(patron, texto, re.IGNORECASE)
            if m:
                monto_str = m.group(1).replace(",", "")
                try:
                    return Decimal(monto_str)
                except Exception:
                    continue
        return None

    @staticmethod
    def _extraer_fecha_bcp(texto: str) -> datetime | None:
        """Parsea fechas en formato BCP: '09 de Abril de 2026 - 02:42 AM'"""
        meses = {
            "enero": 1, "febrero": 2, "marzo": 3, "abril": 4,
            "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
            "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
        }
        patron = r"(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})\s*[-–]\s*(\d{1,2}):(\d{2})\s*(AM|PM)"
        m = re.search(patron, texto, re.IGNORECASE)
        if m:
            dia, mes_str, anio, hora, minuto, ampm = m.groups()
            mes = meses.get(mes_str.lower())
            if mes:
                hora_int = int(hora)
                if ampm.upper() == "PM" and hora_int != 12:
                    hora_int += 12
                elif ampm.upper() == "AM" and hora_int == 12:
                    hora_int = 0
                return datetime(int(anio), mes, int(dia), hora_int, int(minuto))
        return None

    @staticmethod
    def _extraer_fecha_simple(texto: str, patron: str, formato: str) -> datetime | None:
        """Parsea fechas con patrón regex y formato strptime."""
        m = re.search(patron, texto, re.IGNORECASE)
        if m:
            try:
                return datetime.strptime(m.group(1), formato)
            except ValueError:
                return None
        return None
