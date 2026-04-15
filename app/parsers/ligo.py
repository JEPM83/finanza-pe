import re
from datetime import datetime
from app.parsers.base import BaseParser, EmailData, TransaccionParseada


class LigoParser(BaseParser):

    dominios = ["ligo.pe"]

    ASUNTOS_IGNORAR = [
        "bienvenido",
        "estado de cuenta",
    ]

    def puede_parsear(self, email: EmailData) -> bool:
        if not self._es_remitente_valido(email.remitente):
            return False
        if self._es_asunto_ignorable(email.asunto):
            return False
        asunto = email.asunto.lower()
        keywords = ["transferencia", "pago", "consumo", "cargo"]
        return any(k in asunto for k in keywords)

    def parsear(self, email: EmailData) -> list[TransaccionParseada]:
        texto = self._html_a_texto(email.cuerpo_html) if email.cuerpo_html else email.cuerpo_texto
        asunto = email.asunto.lower()

        if "transferencia" in asunto:
            return self._parsear_transferencia(texto, email.fecha_recibido)

        return []

    def _parsear_transferencia(self, texto: str, fecha_fallback: datetime) -> list[TransaccionParseada]:
        monto = self._extraer_monto(texto, [
            r"Monto\s+([\d,]+\.?\d*)",
        ])
        if not monto:
            return []
        op = self._extraer_campo(texto, r"Número de operación\s+(\w+)")
        banco_destino = self._extraer_campo(texto, r"transferencia a\s+([^,]+),")
        fecha = self._extraer_fecha_ligo(texto) or fecha_fallback
        return [TransaccionParseada(
            cuenta_nombre="Tarjeta La Mágica",
            fecha=fecha, monto=monto, moneda="PEN", tipo="cargo",
            descripcion=f"Transferencia Ligo a {banco_destino or 'banco'}",
            numero_operacion=op,
        )]

    def _extraer_fecha_ligo(self, texto: str) -> datetime | None:
        # Formato: "2026-04-07 13:08:54"
        patron = r"(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})"
        m = re.search(patron, texto)
        if m:
            try:
                return datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S")
            except ValueError:
                pass
        return None

    @staticmethod
    def _extraer_campo(texto: str, patron: str) -> str | None:
        m = re.search(patron, texto, re.IGNORECASE)
        return m.group(1).strip() if m else None
