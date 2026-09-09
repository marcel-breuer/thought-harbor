"""Storage adapter factory for API, workers, and future application services."""

from thoughtharbor.storage.service import LocalFileStorage


def get_storage() -> LocalFileStorage:
    """Return the configured local storage adapter."""

    return LocalFileStorage.from_environment()
