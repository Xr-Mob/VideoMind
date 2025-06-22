import asyncio
import re
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import google.generativeai as genai
import os
import re
from dotenv import load_dotenv
from youtube_transcript_api import YouTubeTranscriptApi  # type: ignore
from urllib.parse import urlparse, parse_qs
from typing import List, Optional
import re
import requests
import json

# Load environment variables
load_dotenv()

# Configure Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))  # type: ignore
model = genai.GenerativeModel('gemini-2.5-flash')  # type: ignore  # Using 2.5 flash for text analysis

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

class SummaryTimestamp(BaseModel):
    time: str
    description: str
    seconds: int
    text_position: int  # Position in the summary text

class VideoAnalysisResponse(BaseModel):
    success: bool
    video_url: str
    video_id: str
    video_summary: str
    summary_timestamps: List[SummaryTimestamp]
    has_transcript: bool

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

async def get_video_duration(video_id: str) -> Optional[int]:
    """Fetch video duration from YouTube API"""
    try:
        # You can use YouTube Data API v3 to get video duration
        # For now, we'll use a simple approach with the oEmbed API
        oembed_url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
        response = requests.get(oembed_url, timeout=10)
        
        if response.status_code == 200:
            # Note: oEmbed doesn't provide duration, but we can use it to validate the video exists
            # For actual duration, you'd need YouTube Data API v3 with an API key
            return None  # We'll implement duration validation later
        else:
            print(f"Failed to fetch video info for {video_id}")
            return None
    except Exception as e:
        print(f"Error fetching video duration: {e}")
        return None

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

def time_to_seconds(time_str: str) -> int:
    """Convert time string (MM:SS or HH:MM:SS) to seconds with validation"""
    try:
        parts = time_str.split(':')
        if len(parts) == 2:
            # MM:SS format
            minutes, seconds = map(int, parts)
            if minutes < 0 or seconds < 0 or seconds > 59:
                print(f"Invalid time format: {time_str}")
                return 0
            return minutes * 60 + seconds
        elif len(parts) == 3:
            # HH:MM:SS format
            hours, minutes, seconds = map(int, parts)
            if hours < 0 or minutes < 0 or minutes > 59 or seconds < 0 or seconds > 59:
                print(f"Invalid time format: {time_str}")
                return 0
            return hours * 3600 + minutes * 60 + seconds
        else:
            print(f"Invalid time format: {time_str}")
            return 0
    except (ValueError, TypeError) as e:
        print(f"Error converting time {time_str} to seconds: {e}")
        return 0

def validate_timestamps(timestamps: List[Timestamp], max_duration: Optional[int] = None) -> List[Timestamp]:
    """Validate and filter timestamps to ensure they're within valid ranges"""
    valid_timestamps = []
    
    for ts in timestamps:
        # Basic validation
        if ts.seconds < 0:
            print(f"Skipping timestamp with negative seconds: {ts.time} ({ts.seconds}s)")
            continue
            
        # If we have max duration, validate against it
        if max_duration and ts.seconds > max_duration:
            print(f"Skipping timestamp beyond video duration: {ts.time} ({ts.seconds}s) > {max_duration}s")
            continue
            
        # Validate time format
        if not re.match(r'^\d{1,2}:\d{2}(:\d{2})?$', ts.time):
            print(f"Skipping timestamp with invalid format: {ts.time}")
            continue
            
        valid_timestamps.append(ts)
    
    # Sort by seconds to ensure chronological order
    valid_timestamps.sort(key=lambda x: x.seconds)
    
    print(f"Validated {len(valid_timestamps)} timestamps out of {len(timestamps)}")
    return valid_timestamps

def extract_timestamps_from_summary(summary: str) -> List[SummaryTimestamp]:
    """Extract timestamps from summary text and create SummaryTimestamp objects"""
    timestamps = []
    
    # Pattern to match timestamps at the end of summary points in square brackets
    # Matches patterns like "description here. [1:30]", "bullet point. [2:15]", etc.
    patterns = [
        r'([^[]+?)\s*\[(\d{1,2}:\d{2}(?::\d{2})?)\]',  # "description. [1:30]" or "description. [1:30:45]"
        r'•\s*([^[]+?)\s*\[(\d{1,2}:\d{2}(?::\d{2})?)\]',  # "• bullet point. [1:30]"
    ]
    
    for pattern in patterns:
        matches = re.finditer(pattern, summary, re.IGNORECASE | re.MULTILINE)
        for match in matches:
            description = match.group(1).strip()
            time_str = match.group(2)
            start_pos = match.start()
            
            # Validate time format before processing
            if not re.match(r'^\d{1,2}:\d{2}(:\d{2})?$', time_str):
                print(f"Skipping invalid time format in summary: {time_str}")
                continue
            
            # Convert to seconds and validate
            seconds = time_to_seconds(time_str)
            if seconds == 0 and time_str != "0:00":
                print(f"Skipping invalid timestamp conversion: {time_str}")
                continue
            
            # Clean up description
            description = re.sub(r'\s+', ' ', description)
            if len(description) > 80:
                description = description[:77] + "..."
            
            timestamps.append(SummaryTimestamp(
                time=time_str,
                description=description,
                seconds=seconds,
                text_position=start_pos
            ))
    
    # Remove duplicates and sort by position
    unique_timestamps = []
    seen_positions = set()
    for ts in timestamps:
        if ts.text_position not in seen_positions:
            unique_timestamps.append(ts)
            seen_positions.add(ts.text_position)
    
    # Sort by position and then validate
    sorted_timestamps = sorted(unique_timestamps, key=lambda x: x.text_position)
    
    # Additional validation for summary timestamps
    valid_timestamps = []
    for ts in sorted_timestamps:
        # Basic validation
        if ts.seconds < 0:
            print(f"Skipping summary timestamp with negative seconds: {ts.time}")
            continue
        
        # Reasonable upper limit for summary timestamps (2 hours)
        if ts.seconds > 7200:
            print(f"Skipping summary timestamp beyond reasonable limit: {ts.time} ({ts.seconds}s)")
            continue
        
        valid_timestamps.append(ts)
    
    print(f"Extracted {len(valid_timestamps)} valid timestamps from summary")
    return valid_timestamps

async def generate_video_summary_with_timestamps(transcript: Optional[str], video_url: str) -> tuple[str, List[SummaryTimestamp]]:
    """Generate summary using Gemini with timestamps included"""
    if not transcript:
        # If no transcript, provide a message
        return "Unable to generate summary: No transcript available for this video. The video might not have captions enabled.", []
    
    # Limit transcript length to avoid token limits
    max_chars = 15000
    if len(transcript) > max_chars:
        transcript = transcript[:max_chars] + "..."
    
    prompt = f"""
    Please provide a comprehensive summary of this YouTube video based on its transcript.
    
    IMPORTANT: For each summary point, add the timestamp at the END of that point, not within the text.
    Use this exact format for each summary point:
    
    **Overview:**
    A brief 2-3 sentence overview of what the video is about. (No 0:00 timestamp)
    
    **Key Topics:**
    • Main topic 1 description here. [1:30]
    • Main topic 2 description here. [2:15]
    • Main topic 3 description here. [4:20]
    (Include 3-5 key topics with timestamps at the end of each bullet point)
    
    **Main Takeaways:**
    The most important conclusions or lessons from the video. [3:45]
    Additional key insights worth mentioning. [6:20]
    
    **Notable Details:**
    Any important facts, recommendations, or specific details worth mentioning. [1:30]
    Additional practical examples or demonstrations. [4:15]
    
    Rules:
    - Put timestamps in square brackets at the END of each summary point
    - Use MM:SS format (e.g., [1:30], [4:20])
    - Do NOT put timestamps in the middle of sentences
    - Each bullet point or paragraph should end with its relevant timestamp
    - Keep the summary flowing naturally without timestamp interruptions
    - The topics, along with the timestamps, should be wide-spread throughout the video
    
    Video URL: {video_url}
    
    Transcript: {transcript}
    """
    
    try:
        response = await asyncio.to_thread(
            model.generate_content, prompt
        )
        summary = response.text
        
        # Extract timestamps from the generated summary
        timestamps = extract_timestamps_from_summary(summary)
        
        return summary, timestamps
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
    
    # Get video ID for potential duration validation
    video_id = extract_video_id(video_url)
    video_duration = await get_video_duration(video_id)
    
    prompt = f"""
    Based on the video transcript, create key timestamps that highlight important moments in the video, from the start to the end of the video.
    The timestamps should be wide-spread throughout the video, not just at the beginning or end.

    For each timestamp, provide:
    1. Time in MM:SS format (e.g., "01:30", "05:45")
    2. A brief description of what happens at that moment
    3. The time in seconds for navigation (e.g., 1:30 = 90 seconds)
    
    IMPORTANT: Return ONLY a valid JSON array with this exact format:
    [
        {{"time": "00:00", "description": "Introduction", "seconds": 0}},
        {{"time": "01:30", "description": "Main topic begins", "seconds": 90}},
        {{"time": "03:45", "description": "Key concept explanation", "seconds": 225}},
        {{"time": "05:20", "description": "Practical example", "seconds": 320}},
        {{"time": "07:10", "description": "Conclusion", "seconds": 430}}
        ...
    ]
    
    Rules:
    - Use MM:SS format for time (e.g., "01:30", "05:45")
    - Convert time to seconds correctly (e.g., 1:30 = 90 seconds)
    - Keep descriptions concise but informative
    - Cover the entire video duration
    - Focus on key moments, transitions, and important content
    - Ensure seconds values are accurate and match the time format
    - Do not generate timestamps beyond reasonable video length (max 2 hours = 7200 seconds)
    
    Video URL: {video_url}
    Transcript: {transcript}
    
    Return only the JSON array, no additional text or explanation.
    """
    
    try:
        response = await asyncio.to_thread(
            model.generate_content, prompt
        )
        
        # Extract JSON from the response
        response_text = response.text.strip()
        
        # Try to find JSON array in the response
        import json
        
        # Look for JSON array pattern
        json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
            try:
                timestamps_data = json.loads(json_str)
                
                # Validate and convert to Timestamp objects
                timestamps = []
                for item in timestamps_data:
                    if isinstance(item, dict) and 'time' in item and 'description' in item and 'seconds' in item:
                        # Validate the seconds value matches the time format
                        expected_seconds = time_to_seconds(item['time'])
                        if expected_seconds != item['seconds']:
                            print(f"Warning: Seconds mismatch for {item['time']}. Expected: {expected_seconds}, Got: {item['seconds']}")
                            # Use the calculated value instead
                            item['seconds'] = expected_seconds
                        
                        timestamps.append(Timestamp(
                            time=item['time'],
                            description=item['description'],
                            seconds=item['seconds']
                        ))
                
                # Validate timestamps before returning
                valid_timestamps = validate_timestamps(timestamps, video_duration)
                
                print(f"Generated {len(valid_timestamps)} valid timestamps from Gemini response")
                return valid_timestamps
                
            except json.JSONDecodeError as e:
                print(f"Failed to parse JSON from Gemini response: {e}")
                print(f"Response text: {response_text}")
        
        # Fallback: try to extract timestamps using regex if JSON parsing fails
        print("JSON parsing failed, attempting regex extraction...")
        fallback_timestamps = extract_timestamps_from_text(response_text)
        valid_timestamps = validate_timestamps(fallback_timestamps, video_duration)
        return valid_timestamps
        
    except Exception as e:
        print(f"Error generating timestamps: {e}")
        print(f"Response text: {response.text if hasattr(response, 'text') else 'No response text'}")
        return []

def extract_timestamps_from_text(text: str) -> List[Timestamp]:
    """Extract timestamps from text using regex patterns as fallback"""
    timestamps = []
    
    # Pattern to match timestamp entries in various formats
    patterns = [
        # Pattern for "time": "MM:SS", "description": "...", "seconds": N
        r'"time":\s*"(\d{1,2}:\d{2})",\s*"description":\s*"([^"]+)",\s*"seconds":\s*(\d+)',
        # Pattern for time: "MM:SS", description: "...", seconds: N
        r'time:\s*"(\d{1,2}:\d{2})",\s*description:\s*"([^"]+)",\s*seconds:\s*(\d+)',
        # Pattern for MM:SS - description (seconds: N)
        r'(\d{1,2}:\d{2})\s*-\s*([^"]+)\s*\(seconds:\s*(\d+)\)',
        # Pattern for MM:SS: description
        r'(\d{1,2}:\d{2}):\s*([^\n]+)',
    ]
    
    for pattern in patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE)
        for match in matches:
            time_str = match.group(1)
            description = match.group(2).strip()
            
            # Validate time format
            if not re.match(r'^\d{1,2}:\d{2}(:\d{2})?$', time_str):
                print(f"Skipping invalid time format in regex extraction: {time_str}")
                continue
            
            # Get seconds value
            if len(match.groups()) > 2:
                try:
                    seconds = int(match.group(3))
                    # Validate that seconds match the time format
                    expected_seconds = time_to_seconds(time_str)
                    if expected_seconds != seconds:
                        print(f"Warning: Seconds mismatch in regex extraction. Time: {time_str}, Expected: {expected_seconds}, Got: {seconds}")
                        seconds = expected_seconds
                except (ValueError, TypeError):
                    print(f"Invalid seconds value in regex extraction: {match.group(3)}")
                    seconds = time_to_seconds(time_str)
            else:
                seconds = time_to_seconds(time_str)
            
            # Validate seconds
            if seconds < 0:
                print(f"Skipping timestamp with negative seconds: {time_str}")
                continue
            
            # Reasonable upper limit (2 hours)
            if seconds > 7200:
                print(f"Skipping timestamp beyond reasonable limit: {time_str} ({seconds}s)")
                continue
            
            # Clean up description
            description = re.sub(r'\s+', ' ', description)
            if len(description) > 100:
                description = description[:97] + "..."
            
            timestamps.append(Timestamp(
                time=time_str,
                description=description,
                seconds=seconds
            ))
    
    # Remove duplicates and sort by seconds
    unique_timestamps = []
    seen_times = set()
    for ts in timestamps:
        if ts.time not in seen_times:
            unique_timestamps.append(ts)
            seen_times.add(ts.time)
    
    unique_timestamps.sort(key=lambda x: x.seconds)
    
    print(f"Extracted {len(unique_timestamps)} timestamps using regex fallback")
    return unique_timestamps

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
        
        # Generate summary with timestamps
        print("Generating summary with timestamps using Gemini...")
        summary, summary_timestamps = await generate_video_summary_with_timestamps(transcript, youtube_url)
        
        print("\n--- Gemini AI Response ---")
        print(summary)
        print(f"Extracted {len(summary_timestamps)} timestamps from summary")
        print("--------------------------")
        
        return VideoAnalysisResponse(
            success=True,
            video_url=youtube_url,
            video_id=video_id,
            video_summary=summary,
            summary_timestamps=summary_timestamps,
            has_transcript=bool(transcript)
        )
    
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