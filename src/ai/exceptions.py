class AITransientError(Exception):
    """Erro temporário (429, 503, timeout, etc.)"""


class AIFatalError(Exception):
    """Erro definitivo (prompt inválido, auth, schema, etc.)"""
