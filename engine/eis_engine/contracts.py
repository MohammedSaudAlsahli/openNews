from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Request(StrictModel):
    schema_version: Literal[1]
    request_id: UUID
    command: str = Field(min_length=1, max_length=80)
    payload: dict = Field(default_factory=dict)


class ImportText(StrictModel):
    title: str = Field(min_length=1, max_length=300)
    text: str = Field(min_length=1, max_length=120_000)
    canonical_uri: str = Field(default="", max_length=2000)
    author: str = Field(default="", max_length=200)
    rights_status: Literal["owned", "licensed", "unknown"] = "unknown"
    access_method: Literal["user_paste", "user_file"] = "user_paste"
    purpose: Literal["reference", "style"] = "reference"


class ManualDraft(StrictModel):
    topic: str = Field(min_length=1, max_length=300)
    text: str = Field(min_length=1, max_length=60000)
    format: Literal["x_post", "x_thread", "linkedin", "youtube_long", "shorts", "reels", "tiktok"] = "x_post"
    language: Literal["ar", "en"] = "ar"


class Analyze(StrictModel):
    item_ids: list[UUID] = Field(min_length=1, max_length=100)
    mode: Literal["incremental", "explicit_rebuild"] = "incremental"
    profile_id: UUID | None = None
    model_id: str | None = Field(default=None, min_length=1, max_length=200)
    consent: bool = False
    idempotency_key: UUID


class Profile(StrictModel):
    provider_key: str = Field(min_length=1, max_length=80)
    model_id: str = Field(default="", max_length=200)
    label: str = Field(default="", max_length=120)
    config: dict[str, str] = Field(default_factory=dict)


class Generate(StrictModel):
    topic: str = Field(min_length=3, max_length=2000)
    format: Literal["x_post", "x_thread", "linkedin", "youtube_long", "shorts", "reels", "tiktok"]
    language: Literal["ar", "en"] = "ar"
    profile_id: UUID
    dna_version_id: UUID
    source_ids: list[UUID] = Field(default_factory=list, max_length=12)
    target_seconds: int | None = Field(default=None, ge=10, le=7200)
    max_characters: int = Field(default=280, ge=50, le=25000)
    model_id: str | None = Field(default=None, min_length=1, max_length=200)
    consent: bool = False
    idempotency_key: UUID

    @model_validator(mode="after")
    def duration(self):
        if self.format in {"youtube_long", "shorts", "reels", "tiktok"} and self.target_seconds is None:
            raise ValueError("Video requires target_seconds")
        return self


class Technique(StrictModel):
    category: str
    name: str = Field(min_length=2, max_length=150)
    description: str = Field(min_length=3, max_length=1500)
    applicability: str = Field(min_length=3, max_length=800)
    excerpt: str = Field(min_length=3, max_length=500)
    confidence: float = Field(ge=0, le=1)


class AnalysisResult(StrictModel):
    techniques: list[Technique] = Field(max_length=8)


class Claim(StrictModel):
    text: str
    claim_type: Literal["fact", "interpretation", "opinion"]
    verdict: Literal["supported", "contradicted", "insufficient", "opinion", "needs_review"]
    source_chunk_ids: list[str] = Field(default_factory=list)
    rationale: str
    high_impact: bool = False


class GeneratedDraft(StrictModel):
    text: str = Field(min_length=1, max_length=60000)
    alternatives: list[str] = Field(default_factory=list, max_length=2)
    claims: list[Claim] = Field(default_factory=list, max_length=100)


class Failure(Exception):
    def __init__(self, code: str, message: str):
        self.code, self.message = code, message
        super().__init__(message)


class CustomAgentSave(StrictModel):
    id: UUID | None = None
    name: str = Field(min_length=1, max_length=120)
    instructions: str = Field(min_length=1, max_length=12000)
    profile_id: UUID
    model_id: str = Field(min_length=1, max_length=200)


class ChatSend(StrictModel):
    agent_id: UUID | None = None
    conversation_id: UUID
    message: str = Field(min_length=1, max_length=12000)
    profile_id: UUID
    model_id: str = Field(min_length=1, max_length=200)
    consent: bool = False
    idempotency_key: UUID
    article_ids: list[UUID] = Field(default_factory=list, max_length=12)
    include_news: bool = True
    format: Literal["discussion", "x_posts", "youtube_long", "tiktok"] = "discussion"
    target_seconds: int | None = Field(default=None, ge=10, le=7200)
    days: int = Field(default=7, ge=1, le=31)
    draft_title: str = Field(default="", max_length=300)
    draft_text: str = Field(default="", max_length=60000)


class ChatDraft(StrictModel):
    title: str = Field(min_length=1, max_length=300)
    text: str = Field(min_length=1, max_length=60000)
    format: Literal["x_post", "youtube_long", "tiktok"]
    article_ids: list[str] = Field(default_factory=list, max_length=12)


class ChatReply(StrictModel):
    message: str = Field(min_length=1, max_length=18000)
    article_ids: list[str] = Field(default_factory=list, max_length=12)
    drafts: list[ChatDraft] = Field(default_factory=list, max_length=12)
