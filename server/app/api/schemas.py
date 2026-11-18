"""Request/response models. They mirror spec/openapi.yaml; tests check the two agree."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

LOCALE_PATTERN = r"^[a-z]{2}(-[A-Z]{2})?$"


class ClientInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sdk: str | None = Field(default=None, max_length=40)
    sdk_version: str | None = Field(default=None, max_length=40)
    app_version: str | None = Field(default=None, max_length=40)


class SessionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    locale: str | None = Field(default=None, pattern=LOCALE_PATTERN)
    client: ClientInfo | None = None


class Session(BaseModel):
    session_id: UUID
    app_id: str
    locale: str
    created_at: datetime
    expires_at: datetime


class MessageCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(min_length=1, max_length=2000)
    screen_id: str | None = Field(default=None, max_length=64)
    locale: str | None = Field(default=None, pattern=LOCALE_PATTERN)


class Feedback(BaseModel):
    model_config = ConfigDict(extra="forbid")
    message_id: UUID
    rating: Literal["up", "down"]
    comment: str | None = Field(default=None, max_length=500)


class ManifestStored(BaseModel):
    app_id: str
    version: int
    stored_at: datetime


class Health(BaseModel):
    status: Literal["ok"]
    database: Literal["ok", "unavailable"]
    version: str


class DocArticle(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]{0,63}$")
    title: str = Field(min_length=1, max_length=200)
    screens: list[str] = Field(default_factory=list)
    locale: str = Field(default="en", pattern=LOCALE_PATTERN)
    body: str = Field(min_length=1, max_length=50_000)


class DocsUpload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    articles: list[DocArticle] = Field(min_length=1, max_length=500)


class DocsIngested(BaseModel):
    app_id: str
    articles: int
    chunks: int
    embedder: str
