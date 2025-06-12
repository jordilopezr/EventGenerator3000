import os
import random
import datetime
import logging
import requests
import json
from typing import Optional

DT_API_URL = os.getenv("DT_API_URL", "").rstrip("/")
DT_API_TOKEN = os.getenv("DT_API_TOKEN")

EVENT_TYPES = [
    ("resource", "Resource Metric"),
    ("trace", "Trace + Span"),
    ("http", "HTTP Call"),
    ("db", "DB Call"),
    ("azure", "Azure Service Call"),
    ("error", "Error / Exception"),
    ("warning", "Warning")
]

def check_dynatrace_connection():
    """
    Verifica la conexión y autenticación con la API de Dynatrace.
    Devuelve una tupla (bool_success, str_message).
    """
    if not DT_API_URL or not DT_API_TOKEN:
        return (False, "Error: Las variables de entorno DT_API_URL o DT_API_TOKEN no están configuradas en la Función de Azure.")

    url = f"{DT_API_URL}/api/v2/events/ingest"
    headers = {"Authorization": f"Api-Token {DT_API_TOKEN}"}
    
    try:
        resp = requests.get(url, headers=headers, timeout=5)
        
        if resp.status_code == 405:
            return (True, "Conexión y autenticación con Dynatrace verificadas correctamente.")
        elif resp.status_code == 401:
            return (False, "Error de autenticación (401 Unauthorized). El API Token es inválido o ha expirado.")
        elif resp.status_code == 403:
            return (False, "Permisos insuficientes (403 Forbidden). El API Token no tiene el permiso 'events.ingest'.")
        elif resp.status_code == 404:
            return (False, f"Endpoint no encontrado (404 Not Found). Revisa la URL del entorno: {DT_API_URL}")
        else:
            return (False, f"Respuesta inesperada de la API de Dynatrace: {resp.status_code} {resp.reason}")

    except requests.exceptions.Timeout:
        return (False, "La conexión ha expirado (timeout). Verifica la conectividad de red desde Azure hacia Dynatrace.")
    except requests.exceptions.ConnectionError:
        return (False, f"Error de conexión. No se pudo alcanzar el host: {DT_API_URL}. Revisa la URL y la configuración de red.")
    except Exception as e:
        return (False, f"Ocurrió un error inesperado al conectar: {e}")


def build_payload(evt_code: str):
    ts = int(datetime.datetime.utcnow().timestamp() * 1000)
    common = {
        "timestamp": ts,
        "source": "EventGenerator3000",
        "detect": False
    }

    if evt_code == "resource":
        return {
            "eventType": "RESOURCE_EVENT",
            "entitySelector": "type(HOST),entityName(\"host123\")",
            "property": "CPU_USAGE",
            "value": random.randint(1, 100),
            **common
        }
    if evt_code == "trace":
        return {
            "eventType": "STATE_EVENT",
            "entitySelector": "type(SERVICE),entityName(\"ServiceXYZ\")",
            "state": "TRACE_SPAN",
            "annotationType": "TRACE",
            "annotationDescription": "Simulated span for trace",
            **common
        }
    if evt_code == "http":
        status = random.choice([200, 400, 500])
        return {
            "eventType": "CUSTOM_ANNOTATION",
            "annotationType": "HTTP_CALL",
            "annotationDescription": f"HTTP {status} GET https://example.com/api",
            "customProperties": {
                "statusCode": status,
                "method": "GET",
                "url": "https://example.com/api"
            },
            **common
        }
    if evt_code == "db":
        st = random.choice(["SUCCESS", "FAILURE"])
        return {
            "eventType": "CUSTOM_ANNOTATION",
            "annotationType": "DB_CALL",
            "annotationDescription": f"Simulated DB call: status {st}",
            "customProperties": {
                "database": "MySQL",
                "operation": "SELECT",
                "status": st
            },
            **common
        }
    if evt_code == "azure":
        st = random.choice(["OK", "ERROR"])
        return {
            "eventType": "CUSTOM_ANNOTATION",
            "annotationType": "AZURE_SERVICE",
            "annotationDescription": f"Simulated Azure BlobStorage call: {st}",
            "customProperties": {
                "service": "BlobStorage",
                "operation": "Upload",
                "status": st
            },
            **common
        }
    if evt_code == "error":
        return {
            "eventType": "CUSTOM_ANNOTATION",
            "annotationType": "ERROR",
            "annotationDescription": "Simulated exception occurred",
            "customProperties": {
                "exceptionType": "ValueError",
                "message": "Simulated error"
            },
            **common
        }
    if evt_code == "warning":
        return {
            "eventType": "CUSTOM_ANNOTATION",
            "annotationType": "WARNING",
            "annotationDescription": "Simulated warning",
            "customProperties": {
                "warningCode": "WARN001",
                "message": "Simulated warning"
            },
            **common
        }
    return None

def send_event(payload: dict) -> bool:
    url = f"{DT_API_URL}/api/v2/events/ingest"
    headers = {
        "Authorization": f"Api-Token {DT_API_TOKEN}",
        "Content-Type": "application/json; charset=utf-8"
    }
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=10)
        resp.raise_for_status() 
        return resp.status_code == 200
    except requests.exceptions.RequestException as e:
        logging.error(f"Error sending event to Dynatrace: {e}")
        return False


def render_page(dt_connection_status: tuple, selected: Optional[str] = None, message: Optional[str] = None, status: Optional[str] = None, payload: Optional[dict] = None) -> str:
    options_html = "\n".join(
        f'<option value="{code}"{" selected" if code==selected else ""}>{label}</option>'
        for code, label in EVENT_TYPES
    )

    is_connected, conn_message = dt_connection_status
    conn_status_class = "status-ok" if is_connected else "status-fail"
    connection_html = f"""
    <div class="status-box {conn_status_class}">
        <strong>Estado de Conexión a Dynatrace:</strong>
        <span>{conn_message}</span>
    </div>
    """

    feedback_html = ""
    if message:
        status_class = "status-success" if status == "success" else "status-error"
        feedback_html += f'<div class="message {status_class}"><p>{message}</p></div>'

    payload_html = ""
    if payload:
        payload_str = json.dumps(payload, indent=2)
        payload_html = f'<h3>Payload Enviado</h3><pre><code>{payload_str}</code></pre>'

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Event Generator 3000</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background-color: #f4f7f9;
            color: #333;
            margin: 0;
            padding: 2em;
            display: flex;
            justify-content: center;
            align-items: flex-start;
            min-height: 100vh;
        }}
        .container {{
            background: #fff;
            padding: 2em;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            width: 100%;
            max-width: 700px;
        }}
        h1 {{
            color: #1e3a8a;
            text-align: center;
            margin-top: 0;
            margin-bottom: 1em;
        }}
        .status-box {{
            padding: 1em;
            border-radius: 4px;
            margin-bottom: 1.5em;
            border-left-width: 5px;
            border-left-style: solid;
        }}
        .status-box strong {{ display: block; margin-bottom: 0.25em; }}
        .status-ok {{ background-color: #dcfce7; color: #166534; border-left-color: #22c55e; }}
        .status-fail {{ background-color: #fee2e2; color: #991b1b; border-left-color: #ef4444; }}
        form {{
            display: flex;
            gap: 1em;
            align-items: center;
            margin-bottom: 1.5em;
        }}
        label {{ font-weight: 600; }}
        select, button {{
            padding: 0.8em;
            border: 1px solid #ccc;
            border-radius: 4px;
            font-size: 1em;
        }}
        select {{ flex-grow: 1; }}
        button {{
            background-color: #2563eb; color: white; border: none; cursor: pointer;
            transition: background-color 0.3s ease;
        }}
        button:hover {{ background-color: #1d4ed8; }}
        button:disabled {{ background-color: #9ca3af; cursor: not-allowed; }}
        .message {{ padding: 1em; border-radius: 4px; margin-bottom: 1.5em; }}
        .status-success {{ background-color: #dcfce7; color: #166534; border-left: 5px solid #22c55e; }}
        .status-error {{ background-color: #fee2e2; color: #991b1b; border-left: 5px solid #ef4444; }}
        pre {{
            background-color: #1e293b; color: #e2e8f0; padding: 1em; border-radius: 4px;
            white-space: pre-wrap; word-wrap: break-word; font-family: "Courier New", Courier, monospace;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Event Generator 3000</h1>
        {connection_html}
        <form method="get">
            <label for="type">Selecciona el tipo de evento:</label>
            <select name="type" id="type">
                {options_html}
            </select>
            <button type="submit" {"disabled" if not is_connected else ""}>Generar evento</button>
        </form>
        {feedback_html}
        {payload_html}
    </div>
</body>
</html>"""
import azure.functions as func
def main(req: func.HttpRequest) -> func.HttpResponse:
    dt_connection_status = check_dynatrace_connection()
    
    try:
        evt = req.params.get("type")
        payload = None
        if evt:
            if not dt_connection_status[0]:
                return func.HttpResponse(
                    render_page(dt_connection_status=dt_connection_status, message="No se puede generar el evento porque no hay conexión con Dynatrace.", status="error"),
                    mimetype="text/html", status_code=500
                )

            payload = build_payload(evt)
            if payload and send_event(payload):
                return func.HttpResponse(
                    render_page(dt_connection_status=dt_connection_status, selected=evt, message="¡Evento enviado con éxito!", status="success", payload=payload),
                    mimetype="text/html", status_code=200
                )
            else:
                logging.error("Error al enviar evento o payload inválido")
                return func.HttpResponse(
                    render_page(dt_connection_status=dt_connection_status, selected=evt, message="Error al enviar evento. Revisa la configuración y los logs de la función.", status="error", payload=payload),
                    mimetype="text/html", status_code=500
                )
        else:
            return func.HttpResponse(render_page(dt_connection_status=dt_connection_status), mimetype="text/html")
    except Exception as ex:
        logging.exception("Excepción en la función")
        return func.HttpResponse(
            render_page(dt_connection_status=dt_connection_status, message=f"Ha ocurrido una excepción: {ex}", status="error"),
            mimetype="text/html", status_code=500
        )