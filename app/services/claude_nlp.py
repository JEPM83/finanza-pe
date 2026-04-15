"""
Procesamiento de lenguaje natural con Claude Tool Use.
Claude interpreta el mensaje del usuario y decide qué herramientas usar.
"""
import json
import logging
from anthropic import Anthropic
from app.config import get_settings
from app.services import herramientas_db as db_tools

logger = logging.getLogger(__name__)
settings = get_settings()

SYSTEM_PROMPT = """Eres el asistente financiero personal de Julian Eduardo (Perú).
Tienes acceso a herramientas para consultar su base de datos financiera en tiempo real.

Reglas:
- Responde siempre en español, de forma concisa y clara
- Usa los datos REALES de las herramientas, nunca inventes cifras
- Formatea los montos con separador de miles: S/ 1,234.50
- Para balances negativos (deuda) usa signos negativos o la palabra "deuda"
- Cuando registres un gasto/ingreso, confirma los datos antes de proceder
- Si el usuario saluda o hace preguntas generales, responde amablemente y sugiere qué puede consultar
- Usa emojis con moderación para hacer las respuestas más legibles
"""

# Definición de herramientas para Claude
TOOLS = [
    {
        "name": "obtener_balance",
        "description": "Obtiene el saldo actual de todas las cuentas bancarias, tarjetas y billeteras. Incluye total consolidado en soles.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "obtener_gastos_por_categoria",
        "description": "Obtiene los gastos agrupados por categoría para un período. Útil para 'cuánto gasté en X' o 'mis gastos de este mes'.",
        "input_schema": {
            "type": "object",
            "properties": {
                "periodo": {
                    "type": "string",
                    "enum": ["hoy", "esta_semana", "este_mes", "mes_pasado"],
                    "description": "Período a consultar",
                }
            },
            "required": ["periodo"],
        },
    },
    {
        "name": "obtener_transacciones_recientes",
        "description": "Lista las últimas transacciones. Se puede filtrar por cuenta o tipo.",
        "input_schema": {
            "type": "object",
            "properties": {
                "limite": {
                    "type": "integer",
                    "description": "Número de transacciones a mostrar (máx 20)",
                    "default": 10,
                },
                "cuenta_nombre": {
                    "type": "string",
                    "description": "Filtrar por nombre de cuenta (ej: 'BCP', 'Yape', 'Visa Oro')",
                },
                "tipo": {
                    "type": "string",
                    "enum": ["cargo", "abono"],
                    "description": "Filtrar por tipo de transacción",
                },
            },
            "required": [],
        },
    },
    {
        "name": "obtener_deuda_tarjetas",
        "description": "Muestra el saldo adeudado en cada tarjeta de crédito (Visa Oro BCP, Visa Infiniti Interbank, Ligo).",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "obtener_resumen_periodo",
        "description": "Resumen financiero del período: total ingresos, gastos y balance neto.",
        "input_schema": {
            "type": "object",
            "properties": {
                "periodo": {
                    "type": "string",
                    "enum": ["hoy", "esta_semana", "este_mes", "mes_pasado"],
                    "description": "Período a resumir",
                }
            },
            "required": ["periodo"],
        },
    },
    {
        "name": "buscar_transacciones",
        "description": "Busca transacciones por texto en descripción o comercio. Útil para 'cuánto gasté en Rappi' o 'mis pagos a Netflix'.",
        "input_schema": {
            "type": "object",
            "properties": {
                "busqueda": {
                    "type": "string",
                    "description": "Texto a buscar (nombre de comercio, tipo de gasto, etc.)",
                },
                "limite": {
                    "type": "integer",
                    "description": "Número máximo de resultados",
                    "default": 10,
                },
            },
            "required": ["busqueda"],
        },
    },
    {
        "name": "registrar_transaccion_efectivo",
        "description": "Registra un gasto o ingreso en efectivo manualmente. Usar cuando el usuario dice 'gasté X en Y' o 'recibí X soles'.",
        "input_schema": {
            "type": "object",
            "properties": {
                "tipo": {
                    "type": "string",
                    "enum": ["cargo", "abono"],
                    "description": "cargo=gasto, abono=ingreso",
                },
                "monto": {
                    "type": "number",
                    "description": "Monto en soles",
                },
                "descripcion": {
                    "type": "string",
                    "description": "Descripción del gasto o ingreso",
                },
                "categoria_nombre": {
                    "type": "string",
                    "description": "Categoría: Alimentación, Delivery, Transporte, Supermercado, Telecomunicaciones, Servicios, Entretenimiento, Salud, Educación, Compras, Viajes, Transferencias, Otros",
                    "default": "Otros",
                },
            },
            "required": ["tipo", "monto", "descripcion"],
        },
    },
]

# Mapa de herramientas a funciones
TOOL_FUNCTIONS = {
    "obtener_balance":                db_tools.obtener_balance,
    "obtener_gastos_por_categoria":   db_tools.obtener_gastos_por_categoria,
    "obtener_transacciones_recientes":db_tools.obtener_transacciones_recientes,
    "obtener_deuda_tarjetas":         db_tools.obtener_deuda_tarjetas,
    "obtener_resumen_periodo":        db_tools.obtener_resumen_periodo,
    "buscar_transacciones":           db_tools.buscar_transacciones,
    "registrar_transaccion_efectivo": db_tools.registrar_transaccion_efectivo,
}


def procesar_mensaje(mensaje_usuario: str) -> str:
    """
    Procesa un mensaje del usuario con Claude Tool Use.
    Retorna la respuesta en texto para enviar por WhatsApp.
    """
    if not settings.anthropic_api_key or settings.anthropic_api_key.startswith("sk-ant-REEMPLAZA"):
        return "API de Claude no configurada. Agrega ANTHROPIC_API_KEY en el archivo .env"

    client = Anthropic(api_key=settings.anthropic_api_key)
    messages = [{"role": "user", "content": mensaje_usuario}]

    try:
        # Bucle de tool use: Claude puede llamar múltiples herramientas
        while True:
            response = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=1024,
                system=SYSTEM_PROMPT,
                tools=TOOLS,
                messages=messages,
            )

            # Si Claude terminó sin usar herramientas
            if response.stop_reason == "end_turn":
                texto = " ".join(
                    block.text for block in response.content
                    if hasattr(block, "text")
                )
                return texto.strip()

            # Si Claude quiere usar herramientas
            if response.stop_reason == "tool_use":
                messages.append({"role": "assistant", "content": response.content})
                tool_results = []

                for block in response.content:
                    if block.type != "tool_use":
                        continue

                    tool_name = block.name
                    tool_input = block.input
                    logger.info(f"Claude usa herramienta: {tool_name}({tool_input})")

                    fn = TOOL_FUNCTIONS.get(tool_name)
                    if fn:
                        try:
                            resultado = fn(**tool_input)
                        except Exception as e:
                            resultado = {"error": str(e)}
                    else:
                        resultado = {"error": f"Herramienta {tool_name} no encontrada"}

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(resultado, ensure_ascii=False),
                    })

                messages.append({"role": "user", "content": tool_results})
                continue

            # Stop reason inesperado
            break

        return "No pude procesar tu consulta. Intenta de nuevo."

    except Exception as e:
        logger.error(f"Error en Claude NLP: {e}")
        return f"Error procesando tu consulta: {str(e)[:100]}"
