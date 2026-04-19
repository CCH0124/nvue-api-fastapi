## O11y

|套件名稱|用途說明|
|---|---|
|opentelemetry-api|定義追蹤、指標的核心介面，手動埋點時呼叫 get_tracer 需用到。|
|opentelemetry-sdk|OpenTelemetry 的具體實作，處理 Span 的生成與生命週期管理。|
|opentelemetry-exporter-otlp|將追蹤與日誌數據發送到相容 OTLP 的後端伺服器。|
|opentelemetry-instrumentation-fastapi|自動擷取 FastAPI 路由的 HTTP 資訊、狀態碼與延遲。|
|opentelemetry-instrumentation-httpx|自動在 HTTPX 請求中注入 traceparent 標頭以達成跨服務追蹤。|
|opentelemetry-exporter-prometheus|在 FastAPI 應用中建立 /metrics 端點供 Prometheus 抓取數據。|