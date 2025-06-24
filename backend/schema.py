from sre_constants import SUCCESS
from urllib import response
from mediapipe.calculators import video
from pydantic import BaseModel, Field
from typing import Optional, List

class UrlAnalyzeRequest(BaseModel):
    youtube_url: str

class ChatRequest(BaseModel):
    video_url: str
    query: str

class TimestampsRequest(BaseModel):
    video_url: str

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