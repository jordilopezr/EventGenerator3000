import os
import random
import datetime
import logging
import azure.functions as func
import requests
import json

DT_API_URL = os.getenv("DT_API_URL").rstrip("/")
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
        resp.raise_for_status() # Lanza una excepción para códigos de error HTTP (4xx o 5xx)
        return resp.status_code == 200
    except requests.exceptions.RequestException as e:
        logging.error(f"Error sending event to Dynatrace: {e}")
        return False


def render_page(selected: str = None, message: str = None, status: str = None, payload: dict = None) -> str:
    options_html = "\n".join(
        f'<option value="{code}"{" selected" if code==selected else ""}>{label}</option>'
        for code, label in EVENT_TYPES
    )

    feedback_html = ""
    if message:
        status_class = "status-success" if status == "success" else "status-error"
        feedback_html += f'<div class="message {status_class}"><p>{message}</p></div>'

    payload_html = ""
    if payload:
        # Escapar caracteres HTML en el JSON para mostrarlo de forma segura
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
            max-width: 600px;
        }}
        h1 {{
            color: #1e3a8a; /* Azul oscuro */
            text-align: center;
            margin-top: 0;
        }}
        form {{
            display: flex;
            gap: 1em;
            align-items: center;
            margin-bottom: 1.5em;
        }}
        label {{
            font-weight: 600;
        }}
        select, button {{
            padding: 0.8em;
            border: 1px solid #ccc;
            border-radius: 4px;
            font-size: 1em;
        }}
        select {{
            flex-grow: 1;
        }}
        button {{
            background-color: #2563eb; /* Azul brillante */
            color: white;
            border: none;
            cursor: pointer;
            transition: background-color 0.3s ease;
        }}
        button:hover {{
            background-color: #1d4ed8; /* Azul más oscuro */
        }}
        .message {{
            padding: 1em;
            border-radius: 4px;
            margin-bottom: 1.5em;
        }}
        .status-success {{
            background-color: #dcfce7; /* Verde claro */
            color: #166534; /* Verde oscuro */
            border-left: 5px solid #22c55e;
        }}
        .status-error {{
            background-color: #fee2e2; /* Rojo claro */
            color: #991b1b; /* Rojo oscuro */
            border-left: 5px solid #ef4444;
        }}
        pre {{
            background-color: #1e293b; /* Gris azulado oscuro */
            color: #e2e8f0; /* Gris claro */
            padding: 1em;
            border-radius: 4px;
            white-space: pre-wrap;
            word-wrap: break-word;
            font-family: "Courier New", Courier, monospace;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Event Generator 3000</h1>
        <form method="get">
            <label for="type">Selecciona el tipo de evento:</label>
            <select name="type" id="type">
                {options_html}
            </select>
            <button type="submit">Generar evento</button>
        </form>
        {feedback_html}
        {payload_html}
    </div>
</body>
</html>"""

def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        evt = req.params.get("type")
        payload = None
        if evt:
            payload = build_payload(evt)
            if payload and send_event(payload):
                return func.HttpResponse(
                    render_page(selected=evt, message="¡Evento enviado con éxito!", status="success", payload=payload),
                    mimetype="text/html", status_code=200
                )
            else:
                logging.error("Error al enviar evento o payload inválido")
                return func.HttpResponse(
                    render_page(selected=evt, message="Error al enviar evento. Revisa la configuración y los logs de la función.", status="error", payload=payload),
                    mimetype="text/html", status_code=500
                )
        else:
            # Carga inicial de la página
            return func.HttpResponse(render_page(), mimetype="text/html")
    except Exception as ex:
        logging.exception("Excepción en la función")
        return func.HttpResponse(
            render_page(message=f"Ha ocurrido una excepción: {ex}", status="error"),
            mimetype="text/html", status_code=500
        )
