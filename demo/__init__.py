import os
import json
import requests
import azure.functions as func
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource, SERVICE_NAME
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.dynatrace import DynatraceExporter
from opentelemetry.instrumentation.requests import RequestsInstrumentor

# Configure Tracer Provider
resource = Resource({SERVICE_NAME: "httpbin-proxy-func"})
provider = TracerProvider(resource=resource)
exporter = DynatraceExporter(
    api_url=os.getenv("DT_API_URL"),
    api_token=os.getenv("DT_API_TOKEN"),
    verify_ssl=False
)
processor = BatchSpanProcessor(exporter)
provider.add_span_processor(processor)
trace.set_tracer_provider(provider)
tracer = trace.get_tracer(__name__)

# Instrument outgoing HTTP calls via requests
RequestsInstrumentor().instrument(tracer_provider=provider)


def main(req: func.HttpRequest) -> func.HttpResponse:
    with tracer.start_as_current_span("httpbin_request") as span:
        # Hard-coded proxy and certificate path
        proxy_url = "http://proxy.sig.umbrella.com:443"
        proxies = {"http": proxy_url, "https": proxy_url}
        cert_path = os.path.join('/var/ssl/certs', 'C5091132E9ADF8AD3E33932AE60A5C8FA939E824.der')
        span.set_attribute("proxy.url", proxy_url)

        try:
            # Perform request via proxy using provided cert
            resp = requests.get(
                "https://httpbin.org/get",
                proxies=proxies,
                verify=cert_path,
                timeout=10
            )
            span.set_attribute("http.status_code", resp.status_code)
            data = resp.json()
            span.add_event("Received httpbin response", {"response": data})
            success = True
        except Exception as e:
            span.record_exception(e)
            data = {"error": str(e)}
            span.add_event("httpbin request failed", {"error": str(e)})
            success = False

    # Trigger an explicit export span
    with tracer.start_as_current_span("export_to_dynatrace") as export_span:
        export_span.add_event("Initiated export to Dynatrace")

    # Build a summary payload for the HTTP response
    summary = {
        "function": "httpbin-proxy-func",
        "success": success,
        "httpbin_data": data
    }

    return func.HttpResponse(
        json.dumps(summary),
        status_code=200 if success else 500,
        mimetype="application/json"
    )