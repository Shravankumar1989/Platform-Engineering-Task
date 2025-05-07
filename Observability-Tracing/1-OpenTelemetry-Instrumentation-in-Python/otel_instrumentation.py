import time
from opentelemetry import trace, baggage
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.semconv.resource import ResourceAttributes


def setup_opentelemetry():
    """Configure OpenTelemetry with OTLP exporter pointing to local collector."""
    # Define service name and version in resource
    resource = Resource.create({
        ResourceAttributes.SERVICE_NAME: "payment-service",
        ResourceAttributes.SERVICE_VERSION: "0.1.0",
    })

    # Create a trace provider with the resource
    trace_provider = TracerProvider(resource=resource)
    
    # Create an OTLP exporter sending to local collector
    otlp_exporter = OTLPSpanExporter(
        endpoint="http://localhost:4317",  # Default OTLP gRPC endpoint
        insecure=True  # For local development, no TLS
    )
    
    # Create a BatchSpanProcessor for efficient sending of spans
    span_processor = BatchSpanProcessor(otlp_exporter)
    
    # Add the span processor to the trace provider
    trace_provider.add_span_processor(span_processor)
    
    # Set the trace provider as the global provider
    trace.set_tracer_provider(trace_provider)
    
    return trace.get_tracer(__name__)


def process_payment(user_id, amount, payment_method="credit_card"):
    """
    Process a payment for the given user.
    
    Args:
        user_id (str): The ID of the user making the payment
        amount (float): The payment amount
        payment_method (str): The payment method used
    
    Returns:
        bool: Whether the payment was successful
    """
    # Set up the tracer
    tracer = setup_opentelemetry()
    
    # Set baggage with user_id
    baggage.set_baggage("user.id", user_id)
    
    # Create a span for the payment processing
    with tracer.start_as_current_span("process_payment") as span:
        # Add custom attributes to the span
        span.set_attribute("payment.method", payment_method)
        span.set_attribute("payment.amount", amount)
        span.set_attribute("user.id", user_id)
        
        # Record the start of payment processing
        span.add_event("payment_processing_started")
        
        # Simulate payment processing
        try:
            # Simulate API call to payment gateway
            with tracer.start_as_current_span("payment_gateway_request") as gateway_span:
                gateway_span.set_attribute("gateway.name", "stripe")
                time.sleep(0.3)  # Simulate network delay
            
            # Simulate database update
            with tracer.start_as_current_span("database_update") as db_span:
                db_span.set_attribute("db.operation", "update")
                db_span.set_attribute("db.table", "payments")
                time.sleep(0.2)  # Simulate database operation
            
            # Record successful payment
            span.add_event("payment_successful")
            return True
            
        except Exception as e:
            # Record error in case of failure
            span.record_exception(e)
            span.set_status(trace.StatusCode.ERROR, str(e))
            span.add_event("payment_failed")
            return False


if __name__ == "__main__":
    # Example usage
    success = process_payment(
        user_id="user-123", 
        amount=99.99,
        payment_method="debit_card"
    )
    print(f"Payment successful: {success}")

"""
Install OpenTelemetry packages:

pip install opentelemetry-api opentelemetry-sdk \
            opentelemetry-exporter-otlp \
            opentelemetry-exporter-otlp-proto-grpc
"""