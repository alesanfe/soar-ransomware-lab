from fastapi import FastAPI
from soar_lab.interfaces.api import app, create_app

__all__ = ["app", "create_app"]

# Expose a FastAPI app instance for uvicorn and integration tests.
app: FastAPI = app
