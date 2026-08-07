# How we built the Northwind AI assistant

Our assistant uses Retrieval-Augmented Generation over our internal docs and an
external partner knowledge feed. Retrieval is powered by Qdrant; we embed with
an open-weights model. The assistant can call tools (order lookup, customer
lookup, ticket export) through an MCP gateway. We self-host the model with vLLM
on EKS and track everything in MLflow.
