"""Pydantic schemas for admin APIs."""

from typing import Optional
from pydantic import BaseModel, Field


class VoiceActorCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str = Field(default="", max_length=2000)


class VoiceActorUpdate(BaseModel):
    description: Optional[str] = Field(default=None, max_length=2000)
    is_active: Optional[bool] = None


class AliasCreate(BaseModel):
    alias_name: str = Field(min_length=1, max_length=255)
    target_voice_actor_id: int
    priority: int = 0
    description: str = Field(default="", max_length=2000)
