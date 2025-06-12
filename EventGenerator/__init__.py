import os
import random
import datetime
import logging
import azure.functions as func
import requests

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
    resp = requests.post(url, json=payload, headers=headers)
    return resp.status_code == 200

def render_page(selected: str = None, message: str = None) -> str:
    options_html = "\n".join(
        f'<option value="{code}"{" selected" if code==selected else ""}>{label}</option>'
        for code,label in EVENT_TYPES
    )
    desc = ""
    if selected:
        label = dict(EVENT_TYPES)[selected]
        desc = f"<p>Generando evento: <strong>{label}</strong></p>"
    if message:
        desc += f"<p><em>{message}</em></p>"
    return f"""<!DOCTYPE html>
<html>
  <head><title>Event Generator 3000</title></head>
  <body>
    <h1>Event Generator 3000</h1>
    <form method="get">
      <label for="type">Selecciona el tipo de evento:</label>
      <select name="type" id="type">
        {options_html}
      </select>
      <button type="submit">Generar evento</button>
    </form>
    {desc}
  </body>
</html>"""

def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        evt = req.params.get("type")
        if evt:
            payload = build_payload(evt)
            if payload and send_event(payload):
                return func.HttpResponse(
                    render_page(selected=evt, message="¡Evento enviado con éxito!"),
                    mimetype="text/html", status_code=200
                )
            else:
                logging.error("Error al enviar evento o payload inválido")
                return func.HttpResponse(
                    render_page(selected=evt, message="Error al enviar evento."),
                    mimetype="text/html", status_code=500
                )
        else:
            # primera carga
            return func.HttpResponse(render_page(), mimetype="text/html")
    except Exception as ex:
        logging.exception("Excepción en la función")
        return func.HttpResponse(
            render_page(message=f"Excepción: {ex}"),
            mimetype="text/html", status_code=500
        )
