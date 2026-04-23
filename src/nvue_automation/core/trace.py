import functools
import time
from typing import Any, Callable, Optional
from fastapi import Request, Response
from opentelemetry import trace
from starlette.middleware.base import BaseHTTPMiddleware

tracer = trace.get_tracer(__name__)

class TracingHeaderMiddleware(BaseHTTPMiddleware):
    """
    Middleware to inject OpenTelemetry Trace ID into response headers for correlation.
    This allows clients and downstream services to correlate requests with their traces.
    """
    async def dispatch(self, request: Request, call_next):

        response: Response = await call_next(request)
        
        current_span = trace.get_current_span()
        span_context = current_span.get_span_context()
        
        if span_context.is_valid:
            trace_id = format(span_context.trace_id, '032x')
            response.headers["X-Trace-Id"] = trace_id
            
        return response

def add_span_attributes(event_name: Optional[str] = None, **attributes: Any):
    """
    inject attributes into the current active span. Optionally, add an event with the same attributes.
    """
    current_span = trace.get_current_span()
    if not current_span.is_recording():
        return

    prefix = "app.business"
    processed_attrs = {f"{prefix}.{k}": v for k, v in attributes.items() if v is not None}
    
    current_span.set_attributes(processed_attrs)
    
    if event_name:
        current_span.add_event(event_name, processed_attrs)

def trace_span_attributes(event_name: Optional[str] = None, **arg_mapping: str):
    """
    automatically extract function arguments and add them as span attributes
    using a mapping of attribute keys to argument names.
    
    Example usage:
        @trace_span_attributes(event_name="apply_config", rev_id="revision_id")
        async def apply_config(self, revision_id: str, data: dict):
            ...
    
    This will automatically extract the revision_id value when the function is called and store it in the Span,
    with the key app.business.rev_id.
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            import inspect
            sig = inspect.signature(func)
            bound_args = sig.bind(*args, **kwargs)
            bound_args.apply_defaults()

            attributes_to_add = {}
            for attr_key, arg_name in arg_mapping.items():
                if arg_name in bound_args.arguments:
                    attributes_to_add[attr_key] = bound_args.arguments[arg_name]

            add_span_attributes(event_name=event_name, **attributes_to_add)
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator
