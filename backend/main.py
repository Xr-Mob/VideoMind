import asyncio
import re
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
import re

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

class QuestionRequest(BaseModel):
    video_url: str
    question: str

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

def time_to_seconds(time_str: str) -> int:
    """Convert time string (MM:SS or HH:MM:SS) to seconds"""
    parts = time_str.split(':')
    if len(parts) == 2:
        # MM:SS format
        minutes, seconds = map(int, parts)
        return minutes * 60 + seconds
    elif len(parts) == 3:
        # HH:MM:SS format
        hours, minutes, seconds = map(int, parts)
        return hours * 3600 + minutes * 60 + seconds
    else:
        return 0

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
            
            # Clean up description
            description = re.sub(r'\s+', ' ', description)
            if len(description) > 80:
                description = description[:77] + "..."
            
            timestamps.append(SummaryTimestamp(
                time=time_str,
                description=description,
                seconds=time_to_seconds(time_str),
                text_position=start_pos
            ))
    
    # Remove duplicates and sort by position
    unique_timestamps = []
    seen_positions = set()
    for ts in timestamps:
        if ts.text_position not in seen_positions:
            unique_timestamps.append(ts)
            seen_positions.add(ts.text_position)
    
    return sorted(unique_timestamps, key=lambda x: x.text_position)

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
    A brief 2-3 sentence overview of what the video is about. [0:00]
    
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
    
    prompt = f"""
    Based on the video transcript, create 5-8 key timestamps that highlight important moments in the video.
    
    For each timestamp, provide:
    1. Time in MM:SS format
    2. A brief description of what happens at that moment
    3. The time in seconds for navigation
    
    IMPORTANT: Return ONLY a valid JSON array with this exact format:
    [
        {{"time": "00:00", "description": "Introduction", "seconds": 0}},
        {{"time": "01:30", "description": "Main topic begins", "seconds": 90}},
        {{"time": "03:45", "description": "Key concept explanation", "seconds": 225}},
        {{"time": "05:20", "description": "Practical example", "seconds": 320}},
        {{"time": "07:10", "description": "Conclusion", "seconds": 430}}
    ]
    
    Rules:
    - Use MM:SS format for time (e.g., "01:30", "05:45")
    - Convert time to seconds (e.g., 1:30 = 90 seconds)
    - Keep descriptions concise but informative
    - Cover the entire video duration
    - Focus on key moments, transitions, and important content
    
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
                        timestamps.append(Timestamp(
                            time=item['time'],
                            description=item['description'],
                            seconds=item['seconds']
                        ))
                
                # Sort by seconds to ensure chronological order
                timestamps.sort(key=lambda x: x.seconds)
                
                print(f"Generated {len(timestamps)} timestamps from Gemini response")
                return timestamps
                
            except json.JSONDecodeError as e:
                print(f"Failed to parse JSON from Gemini response: {e}")
                print(f"Response text: {response_text}")
        
        # Fallback: try to extract timestamps using regex if JSON parsing fails
        print("JSON parsing failed, attempting regex extraction...")
        return extract_timestamps_from_text(response_text)
        
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
            seconds = int(match.group(3)) if len(match.groups()) > 2 else time_to_seconds(time_str)
            
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
    api_key = bool(os.getenv("GEMINI_API_KEY"))
    return {
        "status": "healthy",
        "api_key_configured": api_key
    }

def format_time(seconds: float) -> str:
    """Format seconds to MM:SS format"""
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes:02}:{secs:02}"

def generate_timestamp_link(video_url: str, timestamp_str: str) -> str:
    """Generate YouTube timestamp link"""
    try:
        minutes, seconds = map(int, timestamp_str.split(":"))
        total_seconds = minutes * 60 + seconds
        return f"{video_url}&t={total_seconds}s"
    except Exception as e:
        print("Error creating timestamp link:", e)
        return video_url

def hyperlink_timestamps_in_text(answer: str, video_url: str) -> str:
    """Convert timestamps in text to hyperlinks"""
    pattern = r"\b(\d{2}):(\d{2})\b"
    
    def replacer(match):
        ts = match.group(0)
        link = generate_timestamp_link(video_url, ts)
        return f'[{ts}]({link})'
    
    return re.sub(pattern, replacer, answer)

async def answer_question_with_timestamps(
    transcript: list[dict],
    question: str,
    video_url: str
) -> str:
    """Answer questions about video with timestamps"""
    if not transcript:
        return "Sorry, this video has no transcript available."
    
    # Format transcript with timestamps
    def format_chunk(items):
        return "\n".join(f"[{format_time(i['start'])}] {i['text']}" for i in items)
    
    def chunk_transcript(transcript, max_chars=5000):
        chunks, current_chunk, current_len = [], [], 0
        for item in transcript:
            line = f"[{format_time(item['start'])}] {item['text']}\n"
            if current_len + len(line) > max_chars:
                chunks.append(current_chunk)
                current_chunk, current_len = [], 0
            current_chunk.append(item)
            current_len += len(line)
        if current_chunk:
            chunks.append(current_chunk)
        return chunks
    
    chunks = chunk_transcript(transcript)
    print(f"Q&A split into {len(chunks)} chunk(s)")
    
    best_answer = ""
    most_timestamps = 0
    
    for i, chunk in enumerate(chunks):
        chunk_text = format_chunk(chunk)
        prompt = f"""
        You are a helpful assistant answering questions about a YouTube video.
        Use only the transcript below. Include timestamps in MM:SS format when relevant.
        Be concise but comprehensive in your answer.
        
        Transcript:
        {chunk_text}
        
        Question: {question}
        Answer:
        """
        
        try:
            response = await asyncio.to_thread(
                model.generate_content, prompt
            )
            answer = response.text.strip()
            timestamp_count = len(re.findall(r"\b\d{2}:\d{2}\b", answer))
            
            if timestamp_count > most_timestamps:
                best_answer = answer
                most_timestamps = timestamp_count
        except Exception as e:
            print(f"Error answering chunk {i}: {e}")
    
    # Convert timestamps to hyperlinks
    final_answer = hyperlink_timestamps_in_text(
        best_answer or "Sorry, I couldn't find a relevant answer in the video.",
        video_url
    )
    
    return final_answer

@app.post("/ask_question")
async def ask_question(request_data: QuestionRequest):
    """Answer questions about the video with timestamps"""
    video_url = request_data.video_url
    question = request_data.question
    
    # Basic URL validation
    if not video_url.startswith("http") or ("youtube.com" not in video_url and "youtu.be" not in video_url):
        raise HTTPException(status_code=400, detail="Invalid YouTube URL format provided.")
    
    if not question or not question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")
    
    try:
        # Extract video ID
        video_id = extract_video_id(video_url)
        print(f"Extracted video ID: {video_id}")
        
        # Get transcript with timestamps
        print(f"Fetching transcript for Q&A: {video_id}")
        transcript = await get_video_transcript_with_timestamps(video_id)
        
        if not transcript:
            return {
                "success": True,
                "answer": "Sorry, this video has no transcript available. I cannot answer questions without captions.",
                "has_timestamps": False
            }
        
        # Answer the question
        print(f"Answering question: {question}")
        answer = await answer_question_with_timestamps(transcript, question, video_url)
        
        # Check if answer contains timestamps
        has_timestamps = bool(re.search(r"\b\d{2}:\d{2}\b", answer))
        
        return {
            "success": True,
            "answer": answer,
            "has_timestamps": has_timestamps,
            "video_url": video_url,
            "question": question
        }
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"Error during question answering: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to answer question: {str(e)}"
        )