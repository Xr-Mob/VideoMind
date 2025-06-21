'''
This is the python backend using FAST API to process youtube watch URLs with the help of Gemini AI

Contributors:
Jeesmon C - @Xr-Mob

Updated on: 21 June 2025
'''
import asyncio
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import google.generativeai as genai
import os
import re
from dotenv import load_dotenv
from youtube_transcript_api import YouTubeTranscriptApi
from urllib.parse import urlparse, parse_qs
from typing import List, Optional

# Load environment variables
load_dotenv()

# Configure Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-1.5-flash')  # Using 1.5 flash for text analysis

app = FastAPI(
    title="VIDEOMIND-AI",
    description="API for multimodal video analysis",
    version="1.0.0"
)

# Allows CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Request models
class UrlAnalyzeRequest(BaseModel):
    youtube_url: str

class ChatRequest(BaseModel):
    video_url: str
    query: str

class TimestampsRequest(BaseModel):
    video_url: str

# Response models
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

def extract_video_id(youtube_url: str) -> str:
    """Extract video ID from YouTube URL"""
    # Handle different YouTube URL formats
    if "youtu.be" in youtube_url:
        # Short URL format: https://youtu.be/VIDEO_ID
        video_id = youtube_url.split("/")[-1].split("?")[0]
    elif "youtube.com/watch" in youtube_url:
        # Standard format: https://www.youtube.com/watch?v=VIDEO_ID
        parsed_url = urlparse(youtube_url)
        video_id_list = parse_qs(parsed_url.query).get("v")
        if not video_id_list:
            raise ValueError("No video ID found in URL")
        video_id = video_id_list[0]
    else:
        raise ValueError("Invalid YouTube URL format")
    
    return video_id

async def get_video_transcript(video_id: str) -> Optional[str]:
    """Fetch transcript from YouTube"""
    try:
        # Get transcript
        transcript_list = await asyncio.to_thread(
            YouTubeTranscriptApi.get_transcript, video_id
        )
        
        # Combine all text
        full_transcript = " ".join([item['text'] for item in transcript_list])
        return full_transcript
    
    except Exception as e:
        print(f"Error fetching transcript: {e}")
        # Return None if no transcript available
        return None

async def generate_video_summary(transcript: Optional[str], video_url: str) -> str:
    """Generate summary using Gemini"""
    if not transcript:
        # If no transcript, provide a message
        return "Unable to generate summary: No transcript available for this video. The video might not have captions enabled."
    
    # Limit transcript length to avoid token limits
    max_chars = 15000
    if len(transcript) > max_chars:
        transcript = transcript[:max_chars] + "..."
    
    prompt = f"""
    Please provide a comprehensive summary of this YouTube video based on its transcript.
    
    Structure your response as follows:
    
    **Overview:**
    A brief 2-3 sentence overview of what the video is about.
    
    **Key Topics:**
    • Main topic 1
    • Main topic 2
    • Main topic 3
    (Include 3-5 key topics)
    
    **Main Takeaways:**
    The most important conclusions or lessons from the video.
    
    **Notable Details:**
    Any important facts, recommendations, or specific details worth mentioning.
    
    Video URL: {video_url}
    
    Transcript: {transcript}
    """
    
    try:
        response = await asyncio.to_thread(
            model.generate_content, prompt
        )
        return response.text
    except Exception as e:
        print(f"Error generating summary: {e}")
        raise

async def generate_chat_response(transcript: Optional[str], query: str, video_url: str) -> str:
    """Generate chat response using Gemini"""
    if not transcript:
        return "I'm sorry, but I don't have access to the video transcript to answer your question. The video might not have captions enabled."
    
    # Limit transcript length to avoid token limits
    max_chars = 10000
    if len(transcript) > max_chars:
        transcript = transcript[:max_chars] + "..."
    
    prompt = f"""
    You are an AI assistant helping users understand a YouTube video. Answer the user's question based on the video transcript.
    
    Video URL: {video_url}
    User Question: {query}
    
    Video Transcript: {transcript}
    
    Please provide a helpful and accurate answer based on the video content. If the question cannot be answered from the transcript, politely explain that the information is not available in the video.
    """
    
    try:
        response = await asyncio.to_thread(
            model.generate_content, prompt
        )
        return response.text
    except Exception as e:
        print(f"Error generating chat response: {e}")
        raise

async def generate_timestamps(transcript: Optional[str], video_url: str) -> List[Timestamp]:
    """Generate timestamps using Gemini"""
    if not transcript:
        return []
    
    # Limit transcript length to avoid token limits
    max_chars = 8000
    if len(transcript) > max_chars:
        transcript = transcript[:max_chars] + "..."
    
    prompt = f"""
    Based on the video transcript, create 5-8 key timestamps that highlight important moments in the video.
    
    For each timestamp, provide:
    1. Time in MM:SS format
    2. A brief description of what happens at that moment
    3. The time in seconds for navigation
    
    Format your response as a JSON array like this:
    [
        {{"time": "00:00", "description": "Introduction", "seconds": 0}},
        {{"time": "01:30", "description": "Main topic begins", "seconds": 90}}
    ]
    
    Video URL: {video_url}
    Transcript: {transcript}
    """
    
    try:
        response = await asyncio.to_thread(
            model.generate_content, prompt
        )
        
        # Parse the response to extract timestamps
        # For now, return mock timestamps as fallback
        # TODO: Implement proper JSON parsing of Gemini response
        
        return [
            Timestamp(time="00:00", description="Introduction to the video", seconds=0),
            Timestamp(time="00:15", description="Main topic discussion begins", seconds=15),
            Timestamp(time="01:30", description="Key concept explanation", seconds=90),
            Timestamp(time="03:45", description="Practical example demonstration", seconds=225),
            Timestamp(time="05:20", description="Important insights shared", seconds=320),
            Timestamp(time="07:10", description="Conclusion and summary", seconds=430)
        ]
    except Exception as e:
        print(f"Error generating timestamps: {e}")
        return []

@app.post("/analyze_video")
async def analyze_youtube_video(request_data: UrlAnalyzeRequest):
    youtube_url = request_data.youtube_url
    
    # Basic URL validation
    if not youtube_url.startswith("http") or ("youtube.com" not in youtube_url and "youtu.be" not in youtube_url):
        raise HTTPException(status_code=400, detail="Invalid YouTube URL format provided.")
    
    try:
        # Extract video ID
        video_id = extract_video_id(youtube_url)
        print(f"Extracted video ID: {video_id}")
        
        # Get transcript
        print(f"Fetching transcript for video ID: {video_id}")
        transcript = await get_video_transcript(video_id)
        
        if not transcript:
            print("No transcript available for this video")
        
        # Generate summary
        print("Generating summary with Gemini...")
        summary = await generate_video_summary(transcript, youtube_url)
        
        print("\n--- Gemini AI Response ---")
        print(summary)
        print("--------------------------")
        
        return {
            "success": True,
            "video_url": youtube_url,
            "video_id": video_id,
            "video_summary": summary,
            "has_transcript": bool(transcript)
        }
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"An error occurred during video analysis: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Video analysis failed: {str(e)}. Please ensure the video URL is valid and try again."
        )

@app.post("/chat")
async def chat_with_video(request_data: ChatRequest):
    """Process chat queries about a video"""
    video_url = request_data.video_url
    query = request_data.query
    
    if not video_url or not query:
        raise HTTPException(status_code=400, detail="Video URL and query are required.")
    
    try:
        # Extract video ID
        video_id = extract_video_id(video_url)
        
        # Get transcript
        transcript = await get_video_transcript(video_id)
        
        # Generate response
        response = await generate_chat_response(transcript, query, video_url)
        
        return ChatResponse(
            success=True,
            response=response
        )
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"An error occurred during chat: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Chat processing failed: {str(e)}"
        )

@app.post("/timestamps")
async def get_video_timestamps(request_data: TimestampsRequest):
    """Get timestamps for a video"""
    video_url = request_data.video_url
    
    if not video_url:
        raise HTTPException(status_code=400, detail="Video URL is required.")
    
    try:
        # Extract video ID
        video_id = extract_video_id(video_url)
        
        # Get transcript
        transcript = await get_video_transcript(video_id)
        
        # Generate timestamps
        timestamps = await generate_timestamps(transcript, video_url)
        
        return TimestampsResponse(
            success=True,
            timestamps=timestamps
        )
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"An error occurred while generating timestamps: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Timestamp generation failed: {str(e)}"
        )

@app.get("/")
async def read_root():
    return {"message": "VIDEOMIND-AI backend is running!"}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    api_key_configured = bool(os.getenv("GEMINI_API_KEY"))
    return {
        "status": "healthy",
        "api_key_configured": api_key_configured
    }