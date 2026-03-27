import logging
import os
import time
import json
from logging.handlers import RotatingFileHandler
from flask import Flask, request, g
from werkzeug.exceptions import HTTPException

# Configuración básica de logging a consola
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

# crea una instancia de la aplicación Flask, utilizando el nombre del módulo actual para configurar la aplicación correctamente.
app = Flask(__name__)

# protege las cookies y datos de sesion del usuario
app.secret_key = "mysecretkey"

# Logging a archivo (opcional por variables de entorno)
# LOG_FILE=/var/log/junji-inventario.log
# LOG_LEVEL=INFO|DEBUG|WARNING|ERROR
log_file = os.getenv("LOG_FILE")
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
if log_file:
    handler = RotatingFileHandler(log_file, maxBytes=5 * 1024 * 1024, backupCount=5)
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
    app.logger.addHandler(handler)
    app.logger.setLevel(getattr(logging, log_level, logging.INFO))

# Sanitizar datos sensibles antes de loguear
SENSITIVE_KEYS = {"contrasenna", "contrasennaUsuario", "password", "pass", "clave"}


def _scrub_payload(payload):
    if not isinstance(payload, dict):
        return payload
    clean = {}
    for k, v in payload.items():
        if k in SENSITIVE_KEYS:
            clean[k] = "***redacted***"
        else:
            clean[k] = v
    return clean


@app.before_request
def log_request():
    g._start_time = time.time()
    try:
        app.logger.info(
            "[REQ pid=%s] %s %s args=%s form=%s json=%s user=%s",
            os.getpid(),
            request.method,
            request.path,
            dict(request.args),
            _scrub_payload(request.form.to_dict()),
            _scrub_payload(request.get_json(silent=True) or {}),
            getattr(request, "cookies", {}).get("session"),
        )
    except Exception as e:
        app.logger.warning("No se pudo loguear request: %s", e)


@app.after_request
def log_response(response):
    try:
        duration = None
        if hasattr(g, "_start_time"):
            duration = round((time.time() - g._start_time) * 1000, 2)
        app.logger.info(
            "[RES pid=%s] %s %s status=%s duration_ms=%s",
            os.getpid(),
            request.method,
            request.path,
            response.status_code,
            duration,
        )
    except Exception as e:
        app.logger.warning("No se pudo loguear respuesta: %s", e)
    return response


@app.errorhandler(Exception)
def log_exception(e):
    app.logger.exception("Excepción no controlada: %s", e)
    if isinstance(e, HTTPException):
        return e
    return "Error interno del servidor", 500
