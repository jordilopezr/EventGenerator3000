import os
import json
import requests
import azure.functions as func
from requests.exceptions import JSONDecodeError

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource, SERVICE_NAME
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.dynatrace import DynatraceExporter
from opentelemetry.instrumentation.requests import RequestsInstrumentor

# --- Configuración de OpenTelemetry ---

DT_API_URL = os.getenv("DT_API_URL")
DT_API_TOKEN = os.getenv("DT_API_TOKEN")

# MEJORA: Controlar la verificación SSL con una variable de entorno.
# Establece DT_IGNORE_SSL_VERIFICATION a "true" en tu entorno de prueba.
DT_IGNORE_SSL = os.getenv("DT_IGNORE_SSL_VERIFICATION", "false").lower() == "true"
# Por seguridad, si la variable no está, se asume 'false' y SÍ se verifica el SSL.

resource = Resource({SERVICE_NAME: "httpbin-proxy-func"})
provider = TracerProvider(resource=resource)

if DT_API_URL and DT_API_TOKEN:
    # Se usa la variable DT_IGNORE_SSL para decidir si verificar o no.
    # El valor será False solo si DT_IGNORE_SSL_VERIFICATION es "true".
    exporter = DynatraceExporter(
        api_url=DT_API_URL,
        api_token=DT_API_TOKEN,
        verify_ssl=not DT_IGNORE_SSL 
    )
    processor = BatchSpanProcessor(exporter)
    provider.add_span_processor(processor)

trace.set_tracer_provider(provider)
tracer = trace.get_tracer(__name__)

RequestsInstrumentor().instrument(tracer_provider=provider)


def main(req: func.HttpRequest) -> func.HttpResponse:
    # ADVERTENCIA: Se registrará en la traza si la verificación SSL está desactivada.
    if DT_IGNORE_SSL:
        print("ADVERTENCIA: La verificación SSL para el exporter de Dynatrace está DESACTIVADA.")
        trace.get_current_span().set_attribute("security.warning.ssl_verify_disabled", True)

    with tracer.start_as_current_span("httpbin_proxy_function_execution") as parent_span:
        
        proxy_url = os.getenv("PROXY_URL", "http://proxy.sig.umbrella.com:443")
        cert_path = os.getenv("PROXY_CERT_PATH")

        proxies = {"http": proxy_url, "https": proxy_url}
        parent_span.set_attribute("proxy.url", proxy_url)
        
        data = None
        success = False
        status_code_to_return = 500

        try:
            resp = requests.get(
                "https://httpbin.org/get",
                proxies=proxies,
                verify=cert_path,
                timeout=10
            )
            
            parent_span.set_attribute("http.status_code", resp.status_code)
            resp.raise_for_status()

            try:
                data = resp.json()
                parent_span.add_event("Successfully parsed JSON response")
            except JSONDecodeError as json_e:
                parent_span.record_exception(json_e)
                data = {"error": "Failed to decode JSON response", "response_text": resp.text}
                
            success = True
            status_code_to_return = resp.status_code

        except requests.exceptions.RequestException as e:
            parent_span.record_exception(e)
            data = {"error": str(e)}
        
        except Exception as e:
            parent_span.record_exception(e)
            data = {"error": f"An unexpected error occurred: {str(e)}"}

    summary = {
        "function_name": "httpbin-proxy-func",
        "request_successful": success,
        "response_data": data,
        "ssl_verification_disabled": DT_IGNORE_SSL
    }

    return func.HttpResponse(
        json.dumps(summary),
        status_code=200 if success else status_code_to_return,
        mimetype="application/json"
    )