"""Protocolos de seguridad y uso responsable (EP3, IE8).

1. Minimización de datos personales: los registros de observabilidad nunca
   guardan RUT, correos, teléfonos ni números de tarjeta en claro.
2. Guardarraíl de entrada: se rechazan entradas vacías, demasiado largas o con
   patrones de inyección de instrucciones (prompt injection) antes de que
   lleguen al modelo.
"""

import re

from . import config

PATRONES_PII = [
    (re.compile(r"\b\d{1,2}\.?\d{3}\.?\d{3}-[\dkK]\b"), "[RUT]"),
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"), "[CORREO]"),
    (re.compile(r"(?:\+?56\s?)?(?:9\s?\d{4}\s?\d{4}|2\s?\d{4}\s?\d{4})\b"), "[TELEFONO]"),
    (re.compile(r"\b(?:\d{4}[ -]?){3}\d{4}\b"), "[TARJETA]"),
]

PATRONES_INYECCION = [
    r"ignora(?:r)? (?:las |todas las |tus )?(?:instrucciones|reglas)",
    r"olvida(?:r)? (?:las |todas las |tus )?(?:instrucciones|reglas)",
    r"ignore (?:all |the |previous )*instructions",
    r"(?:muestra|revela|imprime|dime) (?:tu |el )?(?:prompt|system prompt|instrucciones del sistema)",
    r"act[uú]a como (?:si no tuvieras|sin) (?:reglas|restricciones)",
    r"modo (?:desarrollador|dan|sin censura)",
    r"<\s*script",
    r"(?:borra|elimina) (?:todos? )?(?:los )?(?:registros|archivos|expedientes)",
    r"autoriza(?:r)? (?:la |esta )?(?:operaci[oó]n|destinaci[oó]n)",
]
_INYECCION = re.compile("|".join(PATRONES_INYECCION), re.IGNORECASE)


def enmascarar(texto) -> str:
    """Reemplaza datos personales por etiquetas antes de registrar un texto."""
    if texto is None:
        return ""
    texto = str(texto)
    for patron, etiqueta in PATRONES_PII:
        texto = patron.sub(etiqueta, texto)
    return texto


def validar_entrada(texto: str) -> tuple[bool, str]:
    """Devuelve (permitida, motivo). Se evalúa antes de cualquier llamada al LLM."""
    limpio = (texto or "").strip()
    if not limpio:
        return False, "entrada vacía"
    if len(limpio) > config.MAX_LARGO_ENTRADA:
        return False, f"entrada de {len(limpio)} caracteres (máximo {config.MAX_LARGO_ENTRADA})"
    coincidencia = _INYECCION.search(limpio)
    if coincidencia:
        return False, f"patrón no permitido: «{coincidencia.group(0)}»"
    return True, ""


MENSAJE_BLOQUEO = (
    "No puedo procesar esa solicitud: {motivo}. Puedo revisar operaciones (por ejemplo, "
    "'Revisa la OP1003'), responder sobre los procedimientos de la agencia o priorizar la cola. "
    "No autorizo operaciones ni modifico registros fuera del flujo de revisión."
)
