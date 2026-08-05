from soar_lab.interfaces.api.composition import CompositionRoot

__all__ = ["CompositionRoot", "create_app"]


def create_app():
    """Factory function to create the FastAPI app with all dependencies."""
    composition = CompositionRoot()
    return composition.create_fastapi_app()
