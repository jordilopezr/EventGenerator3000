import os
import json
import requests
import azure.functions as func
from requests.exceptions import JSONDecodeError

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource, SERVICE_NAME
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.requests import RequestsInstrumentor

# --- Configuración de OpenTelemetry ---
DT_API_URL = os.getenv("DT_API_URL")
DT_API_TOKEN = os.getenv("DT_API_TOKEN")
# Ignorar SSL para Dynatrace si se define la variable DT_IGNORE_SSL_VERIFICATION="true"
DT_IGNORE_SSL = os.getenv("DT_IGNORE_SSL_VERIFICATION", "false").lower() == "true"

# Recurso y provider
resource = Resource({SERVICE_NAME: "httpbin-proxy-func"})
provider = TracerProvider(resource=resource)

if DT_API_URL and DT_API_TOKEN:
    headers = {"Authorization": f"Api-Token {DT_API_TOKEN}"}
    exporter = OTLPSpanExporter(
        endpoint=DT_API_URL,
        headers=headers,
        insecure=DT_IGNORE_SSL
    )
    processor = BatchSpanProcessor(exporter)
    provider.add_span_processor(processor)

trace.set_tracer_provider(provider)
tracer = trace.get_tracer(__name__)

# Instrumentar requests
RequestsInstrumentor().instrument(tracer_provider=provider)


def main(req: func.HttpRequest) -> func.HttpResponse:
    # Registrar advertencia si SSL está deshabilitado
    if DT_IGNORE_SSL:
        trace.get_current_span().set_attribute("security.warning.ssl_verify_disabled", True)

    with tracer.start_as_current_span("httpbin_proxy_function_execution") as span:
        # Proxy y certificado en duro
        proxy_url = "http://proxy.sig.umbrella.com:443"
        cert_path = "/var/ssl/certs/C5091132E9ADF8AD3E33932AE60A5C8FA939E824.der"
        proxies = {"http": proxy_url, "https": proxy_url}
        span.set_attribute("proxy.url", proxy_url)

        try:
            resp = requests.get(
                "https://httpbin.org/get",
                proxies=proxies,
                verify=cert_path,
                timeout=10
            )
            span.set_attribute("http.status_code", resp.status_code)
            resp.raise_for_status()

            try:
                data = resp.json()
                span.add_event("Successfully parsed JSON response", {"data_length": len(json.dumps(data))})
            except JSONDecodeError:
                span.record_exception(JSONDecodeError)
                data = {"error": "Failed to decode JSON response", "response_text": resp.text}

            success = True
            status_code = resp.status_code
        except Exception as e:
            span.record_exception(e)
            data = {"error": str(e)}
            success = False
            status_code = 500

    # Respuesta HTTP con resumen
    summary = {
        "function_name": "httpbin-proxy-func",
        "request_successful": success,
        "response_data": data
    }

    return func.HttpResponse(
        json.dumps(summary),
        status_code=status_code,
        mimetype="application/json"
    )