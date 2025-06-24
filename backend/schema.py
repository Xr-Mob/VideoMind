from sre_constants import SUCCESS
from urllib import response
from mediapipe.calculators import video
from pydantic import BaseModel
from typing import Optional, List

from sklearn.datasets import descr

class UrlAnalyzeRequest(BaseModel):
    youtube_url: str

class ChatRequest(BaseModel):
    video_url: str
    query: str

class TimestampsRequest(BaseModel):
    video_url: str

class VisualSearchRequest(BaseModel):
    youtube_url: str
    search_query: str

class Timestamp(BaseModel):
    time: str
    description: str
    seconds: int

class TimestampsResponse(BaseModel):
    success: bool
    timestamps: List[Timestamp]

class ChatResponse(BaseModel):
    success: bool
    response: str

class SummaryTimestamp(BaseModel):
    time: str
    description: str
    seconds: int
    text_position: int

class VideoAnalysisResponse(BaseModel):
    success: bool
    video_url: str
    video_id: str
    video_summary: str
    summary_timestamps: List[SummaryTimestamp]
    has_transcripts: bool

class VideoDescription(BaseModel):
    timestamps: int
    description: str
    embedding: list[float]

class VideoEmbeddingResponse(BaseModel):
    video_id: str
    descriptions: List[VideoDescription]

class VisualSearchResult(BaseModel):
    timestamp: int
    description: str
    similarity_score: float

class VisualSearchResponse(BaseModel):
    video_id: str
    search_query: str
    results: List[VisualSearchResult]