"""Settings for HTTP-connectors to external services."""

from abc import ABC

from pydantic import BaseModel, Field, HttpUrl


class HttpConnectorSettings(BaseModel, ABC):
    """Base HTTP connector settings."""

    api_key: str | None = Field(None, description="Geocoder API key")
    auth_header: str = Field("X-Authentication", description="Authentication header name")
    base_url: HttpUrl = Field(..., description="External service base URL")
    max_retries_count: int = Field(5, description="Maximum retries count limit")
