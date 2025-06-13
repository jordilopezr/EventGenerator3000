import os
import random
import logging
import datetime
import azure.functions as func
import requests
import json
from typing import Optional

# --- Nuevas importaciones para OpenTelemetry y OneAgent SDK ---
from opentelemetry import trace, metrics
from opentelemetry.trace import Status, StatusCode
import oneagent
from oneagent.sdk.tracers import CustomTracer
# -------------------------------------------------------------

# --- Inicialización de SDKs ---
# La distro de OTel se auto-configura con las variables de entorno OTEL_*.
# El SDK de OneAgent debe ser inicializado. Funciona mejor con un OneAgent activo en el host.
oneagent.initialize()
# -----------------------------

# --- Configuración de Dynatrace ---
DT_API_URL = os.getenv("DT_API_URL", "").rstrip("/")
DT_API_TOKEN = os.getenv("DT_API_TOKEN")
# ----------------------------------

# --- Tipos de Eventos (Ampliados) ---
EVENT_TYPES = [
    # Tipos existentes (API de Eventos v2)
    ("resource", "API - Resource Metric"),
    ("trace", "API - Trace + Span Annotation"),
    ("http", "API - HTTP Call Annotation"),
    ("db", "API - DB Call Annotation"),
    ("azure", "API - Azure Service Call Annotation"),
    ("error", "API - Error / Exception Annotation"),
    ("warning", "API - Warning Annotation"),
    # Nuevos tipos de OpenTelemetry
    ("otel_trace", "OTel - Custom Trace"),
    ("otel_metric", "OTel - Custom Metric (Counter)"),
    # Nuevo tipo para OneAgent SDK
    ("sdk_trace", "SDK - OneAgent Custom Trace")
]
# ----------------------------------

# --- Lógica de OpenTelemetry y OneAgent SDK ---

# OTel: Obtenemos un "tracer" y un "meter" globales.
tracer = trace.get_tracer("event.generator.tracer")
meter = metrics.get_meter("event.generator.meter")
request_counter = meter.create_counter(
    "generated_requests",
    description="Counts the number of generated requests by type",
    unit="1"
)

def generate_otel_trace():
    """Genera una traza de ejemplo con un span padre y un hijo."""
    with tracer.start_as_current_span("generate-event-parent-span") as parent_span:
        parent_span.set_attribute("generator.type", "otel_trace")
        logging.info("Generando traza OTel...")
        with tracer.start_as_current_span("child-span-processing") as child_span:
            child_span.set_attribute("child.attribute", "some_value")
            child_span.add_event("Processing started")
            child_span.set_status(Status(StatusCode.OK))
        parent_span.set_status(Status(StatusCode.OK))
    logging.info("Traza OTel finalizada.")

def generate_otel_metric(event_type: str):
    """Incrementa un contador de métricas con atributos."""
    attrs = {"event_type": event_type, "region": "local"}
    request_counter.add(1, attrs)
    logging.info(f"Métrica OTel generada para el tipo: {event_type}")

def generate_sdk_trace():
    """Genera una traza de ejemplo usando el OneAgent SDK."""
    tracer = oneagent.sdk.create_custom_tracer('MyCustomTracer')
    with tracer.trace_custom_service_method('my_custom_service_method'):
        logging.info("Generando traza con OneAgent SDK...")
        oneagent.sdk.add_custom_request_attribute('service.type', 'EventGeneratorSDK')
    logging.info("Traza de OneAgent SDK finalizada.")

# --- Lógica existente (no modificada) ---

def check_dynatrace_connection():
    if not DT_API_URL or not DT_API_TOKEN:
        return (False, "Error: Las variables de entorno para la API de Eventos (DT_API_URL, DT_API_TOKEN) no están configuradas.")
    url = f"{DT_API_URL}/api/v2/events/ingest"
    headers = {"Authorization": f"Api-Token {DT_API_TOKEN}"}
    try:
        resp = requests.get(url, headers=headers, timeout=5)
        if resp.status_code == 405:
            return (True, "API de Eventos: Conexión y autenticación verificadas.")
        elif resp.status_code == 401: return (False, "API de Eventos: Error de autenticación (401).")
        else: return (False, f"API de Eventos: Respuesta inesperada {resp.status_code}.")
    except requests.exceptions.RequestException:
        return (False, f"API de Eventos: Error de conexión a {DT_API_URL}.")

def build_payload(evt_code: str):
    ts = int(datetime.datetime.utcnow().timestamp() * 1000)
    common = {"timestamp": ts, "source": "EventGenerator3000", "detect": False}
    if evt_code == "resource": return {"eventType": "RESOURCE_EVENT", "entitySelector": "type(HOST),entityName(\"host123\")", "property": "CPU_USAGE", "value": random.randint(1, 100), **common} # type: ignore
    if evt_code == "trace": return {"eventType": "STATE_EVENT", "entitySelector": "type(SERVICE),entityName(\"ServiceXYZ\")", "state": "TRACE_SPAN", "annotationType": "TRACE", **common}
    # ... (resto de la función build_payload sin cambios)...
    if evt_code == "http":
        status = random.choice([200, 400, 500])
        return {"eventType": "CUSTOM_ANNOTATION", "annotationType": "HTTP_CALL", "annotationDescription": f"HTTP {status} GET https://example.com/api", "customProperties": {"statusCode": status, "method": "GET"}, **common}
    if evt_code == "db":
        st = random.choice(["SUCCESS", "FAILURE"])
        return {"eventType": "CUSTOM_ANNOTATION", "annotationType": "DB_CALL", "annotationDescription": f"Simulated DB call: status {st}", "customProperties": {"database": "MySQL", "status": st}, **common}
    if evt_code == "azure":
        st = random.choice(["OK", "ERROR"])
        return {"eventType": "CUSTOM_ANNOTATION", "annotationType": "AZURE_SERVICE", "annotationDescription": f"Simulated Azure BlobStorage call: {st}", "customProperties": {"service": "BlobStorage", "status": st}, **common}
    if evt_code == "error":
        return {"eventType": "CUSTOM_ANNOTATION", "annotationType": "ERROR", "annotationDescription": "Simulated exception occurred", **common}
    if evt_code == "warning":
        return {"eventType": "CUSTOM_ANNOTATION", "annotationType": "WARNING", "annotationDescription": "Simulated warning", **common}
    return None


def send_event(payload: dict) -> bool:
    url = f"{DT_API_URL}/api/v2/events/ingest"
    headers = {"Authorization": f"Api-Token {DT_API_TOKEN}", "Content-Type": "application/json; charset=utf-8"}
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=10)
        resp.raise_for_status()
        return resp.status_code == 200
    except requests.exceptions.RequestException as e:
        logging.error(f"Error sending event to Dynatrace: {e}")
        return False

# --- Renderizado de página (sin cambios significativos) ---
def render_page(dt_connection_status: tuple, selected: Optional[str] = None, message: str = None, status: Optional[str] = None, payload: Optional[dict] = None) -> str:
    # ... (función render_page sin cambios, la dejé igual que en la versión anterior)
    options_html = "\n".join(f'<option value="{code}"{" selected" if code==selected else ""}>{label}</option>' for code, label in EVENT_TYPES)
    is_connected, conn_message = dt_connection_status
    conn_status_class = "status-ok" if is_connected else "status-fail"
    connection_html = f'<div class="status-box {conn_status_class}"><strong>Estado de Conexión a Dynatrace:</strong><span>{conn_message}</span></div>'
    feedback_html = ""
    if message:
        status_class = "status-success" if status == "success" else "status-error"
        feedback_html += f'<div class="message {status_class}"><p>{message}</p></div>'
    payload_html = ""
    if payload:
        payload_str = json.dumps(payload, indent=2)
        payload_html = f'<h3>Payload Enviado (API Eventos)</h3><pre><code>{payload_str}</code></pre>'
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Event Generator 3000</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background-color: #f4f7f9; margin: 0; padding: 2em; display: flex; justify-content: center; align-items: flex-start; min-height: 100vh; }}
        .container {{ background: #fff; padding: 2em; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); width: 100%; max-width: 700px; }}
        h1 {{ color: #1e3a8a; text-align: center; margin-top: 0; margin-bottom: 1em; }}
        .status-box {{ padding: 1em; border-radius: 4px; margin-bottom: 1.5em; border-left: 5px solid; }}
        .status-box strong {{ display: block; margin-bottom: 0.25em; }}
        .status-ok {{ background-color: #dcfce7; color: #166534; border-left-color: #22c55e; }}
        .status-fail {{ background-color: #fee2e2; color: #991b1b; border-left-color: #ef4444; }}
        form {{ display: flex; gap: 1em; align-items: center; margin-bottom: 1.5em; }}
        label {{ font-weight: 600; }}
        select, button {{ padding: 0.8em; border: 1px solid #ccc; border-radius: 4px; font-size: 1em; }}
        select {{ flex-grow: 1; }}
        button {{ background-color: #2563eb; color: white; border: none; cursor: pointer; }}
        button:disabled {{ background-color: #9ca3af; cursor: not-allowed; }}
        .message {{ padding: 1em; border-radius: 4px; margin-bottom: 1.5em; }}
        .status-success {{ background-color: #dcfce7; color: #166534; border-left: 5px solid #22c55e; }}
        .status-error {{ background-color: #fee2e2; color: #991b1b; border-left: 5px solid #ef4444; }}
        pre {{ background-color: #1e293b; color: #e2e8f0; padding: 1em; border-radius: 4px; white-space: pre-wrap; word-wrap: break-word; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Event Generator 3000</h1>{connection_html}
        <form method="get">
            <label for="type">Selecciona el tipo de dato:</label>
            <select name="type" id="type">{options_html}</select>
            <button type="submit">Generar Dato</button>
        </form>
        {feedback_html}
        {payload_html}
    </div>
</body>
</html>"""


# --- Lógica Principal (Actualizada para enrutar) ---
def main(req: func.HttpRequest) -> func.HttpResponse:
    # La conexión a la API de eventos es opcional ahora, pero la verificamos para dar feedback.
    dt_connection_status = check_dynatrace_connection()
    
    try:
        evt = req.params.get("type")
        message = ""
        status_code = 200
        status_str = "success"
        payload_to_show = None

        if evt:
            if evt.startswith("otel_"):
                # --- Rama para OpenTelemetry ---
                if evt == "otel_trace":
                    generate_otel_trace()
                    message = "Traza OpenTelemetry generada con éxito. Revisa tu entorno de Dynatrace."
                elif evt == "otel_metric":
                    generate_otel_metric(evt)
                    message = "Métrica OpenTelemetry generada con éxito. Revisa tu entorno de Dynatrace."
            
            elif evt.startswith("sdk_"):
                # --- Rama para OneAgent SDK ---
                if evt == "sdk_trace":
                    generate_sdk_trace()
                    message = "Traza de OneAgent SDK generada con éxito. Funcionará si un OneAgent está activo en el host."

            else:
                # --- Rama existente para la API de Eventos ---
                if not dt_connection_status[0]:
                    message = "No se puede generar el evento de API porque no hay conexión con Dynatrace."
                    status_str = "error"
                    status_code = 500
                else:
                    payload_to_show = build_payload(evt)
                    if payload_to_show and send_event(payload_to_show):
                        message = "¡Evento de API enviado con éxito!"
                    else:
                        message = "Error al enviar el evento de API."
                        status_str = "error"
                        status_code = 500
            
            return func.HttpResponse(
                render_page(dt_connection_status=dt_connection_status, selected=evt, message=message, status=status_str, payload=payload_to_show),
                mimetype="text/html", status_code=status_code
            )

        else:
            # Carga inicial de la página
            return func.HttpResponse(render_page(dt_connection_status=dt_connection_status), mimetype="text/html")

    except Exception as ex:
        logging.exception("Excepción en la función")
        return func.HttpResponse(
            render_page(dt_connection_status=dt_connection_status, message=f"Ha ocurrido una excepción: {ex}", status="error"),
            mimetype="text/html", status_code=500
        )