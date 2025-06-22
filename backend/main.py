import asyncio
import re
import json
import numpy as np
from pydantic import BaseModel, Field
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import google.generativeai as genai
import os
from dotenv import load_dotenv
from youtube_transcript_api import YouTubeTranscriptApi  # type: ignore
from urllib.parse import urlparse, parse_qs
from typing import List, Optional

# Load environment variables
load_dotenv()

# --- Global In-Memory Storage for Video Embeddings ---
video_embeddings_store = {}

# Configure Gemini
try:
    gen_api_key=os.getenv("GEMINI_API_KEY")
    if not gen_api_key:
        raise ValueError("API Key not found in enviornment variables!")
    genai.configure(api_key=gen_api_key)
    #Text analysis model
    model = genai.GenerativeModel('gemini-2.5-flash')
except ValueError as e:
    print(f"Configuration Error: {e}")
    model =None
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))  # type: ignore
model = genai.GenerativeModel('gemini-1.5-flash')  # type: ignore  # Using 1.5 flash for text analysis

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

class VisualSearchRequest(BaseModel):
    youtube_url: str
    search_query: str

class VideoDescription(BaseModel):
    timestamp: int = Field(description="Timestamp in seconds for the described scene.")
    description: str = Field(description="Textual description of the visual content at this timestamp.")
    embedding: list[float] = Field(description="Embedding vector for the description.")

class VideoEmbeddingsResponse(BaseModel):
    video_id: str
    descriptions: list[VideoDescription]

class VisualSearchResult(BaseModel):
    timestamp: int
    description: str
    similarity_score: float

class VisualSearchResultsResponse(BaseModel):
    video_id: str
    search_query: str
    results: list[VisualSearchResult]

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

# Function to calculate cosine similarity between two vectors
def cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
    """Calculates the cosine similarity between two vectors."""
    v1 = np.array(vec1)
    v2 = np.array(vec2)
    dot_product = np.dot(v1, v2)
    norm_v1 = np.linalg.norm(v1)
    norm_v2 = np.linalg.norm(v2)
    if norm_v1 == 0 or norm_v2 == 0:
        return 0.0 # Avoid division by zero
    return dot_product / (norm_v1 * norm_v2)

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
    Based on the video transcript, create key timestamps that highlight important moments in the video.
    
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
    - Prioritize logical and thematic boundaries when splitting the transcript (e.g., new topic, question, or segment).
    - Avoid over-segmenting long videos; prefer **fewer, more meaningful sections**.
    - For a 10-minute video, return around **3–5** sections.
    - For a 30-minute video, return around **6–10** sections.
    - For a 1-hour video, return around **8–15** sections.
    - For a 2-hour video, return around **10–18** sections.
    - Typical section length should be **3–6 minutes**, but allow longer if the topic continues.
    - **Do not create sections shorter than 1 minute**, unless there's a clear, standalone transition or shift.
    
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
    
@app.post("/generate_embeddings", response_model=VideoEmbeddingsResponse)
async def generate_video_descriptions_and_embeddings(youtube_url_data: UrlAnalyzeRequest):
    youtube_url_string = youtube_url_data.youtube_url
    video_id = extract_video_id(youtube_url_string)
    if not video_id:
        raise HTTPException(status_code=400, detail="Invalid YouTube URL provided.")

    if not model:
        raise HTTPException(status_code=500, detail="Gemini AI video understanding model not initialized. Check API key.")

    try:
        description_prompt = """
        You are video analysis. For the provided video, generate a list of detailed visual descriptions for key moments, scenes, clothes, colors etc with accurate timestamps. Never provide a timestamp which is not in range of the video.
        For each description, provide a timestamp in seconds when the scene occurs. Aim for as many distinct descriptions covering different parts of the video's visual content, but never cross the limit of 200. 

        Format your response as a JSON array of objects, where each object has:
        - "timestamp": integer (seconds from the start of the video)
        - "description": string (a detailed visual description of the scene)

        Use MM:SS format for time.
        
        Example JSON structure:
        [
            {
                "timestamp": 1:10,
                "description": "A wide shot of a cityscape with towering skyscrapers under a clear blue sky."
            },
            {
                "timestamp": 00:45,
                "description": "A close-up of a person's hands typing rapidly on a glowing holographic keyboard."
            }
        ]
        """
        
        print(f"Generating visual descriptions for '{youtube_url_string}' using 'gemini-2.0-flash'...")

        gemini_response = await asyncio.to_thread(
            lambda: model.generate_content( # Using video_understanding_model
                contents=[
                    {
                        "file_data": {
                            "file_uri": youtube_url_string,
                            "mime_type": "video/mp4"
                        }
                    },
                    {"text": description_prompt}
                ],
                generation_config={
                    "response_mime_type": "application/json",
                    "response_schema": {
                        "type": "ARRAY",
                        "items": {
                            "type": "OBJECT",
                            "properties": {
                                "timestamp": {"type": "INTEGER"},
                                "description": {"type": "STRING"}
                            },
                            "required": ["timestamp", "description"]
                        }
                    }
                }
            )
        )

        raw_descriptions_json = gemini_response.candidates[0].content.parts[0].text
        parsed_descriptions = json.loads(raw_descriptions_json)

        # Generate embeddings for each description and store them
        embedded_descriptions = []
        for desc_obj in parsed_descriptions:
            description_text = desc_obj["description"]
            timestamp = desc_obj["timestamp"]

            print(f"Embedding description for timestamp {timestamp}: '{description_text[:50]}...'")
            
            embedding_response = await asyncio.to_thread(
                lambda: genai.embed_content(
                    model='models/embedding-001',
                    content=description_text,
                    task_type="RETRIEVAL_DOCUMENT"
                )
            )
            embedding_vector = embedding_response['embedding']
            
            # Create a VideoDescription object and append
            vd = VideoDescription(
                timestamp=timestamp,
                description=description_text,
                embedding=embedding_vector
            )
            embedded_descriptions.append(vd)
        
        # Store the generated embeddings in the global store for later search
        video_embeddings_store[video_id] = embedded_descriptions
        print(f"Stored {len(embedded_descriptions)} visual descriptions for video ID: {video_id}")

        return VideoEmbeddingsResponse(video_id=video_id, descriptions=embedded_descriptions)

    except Exception as e:
        print(f"An error occurred during video description and embedding generation: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate video descriptions and embeddings: {e}. "
                   "Ensure the video is public and accessible, and Gemini API key is valid."
        )

# NEW ENDPOINT: Perform Natural Language Visual Search
@app.post("/perform_visual_search", response_model=VisualSearchResultsResponse)
async def perform_visual_search(request_data: VisualSearchRequest):
    video_url_to_search = request_data.youtube_url
    search_query = request_data.search_query

    try:
        video_id = extract_video_id(video_url_to_search)
        if not video_id:
            raise HTTPException(status_code=400, detail="Invalid YouTube URL provided for search.")

        # Check if embeddings for this video are already stored
        if video_id not in video_embeddings_store or not video_embeddings_store[video_id]:
            raise HTTPException(
                status_code=404,
                detail=f"No visual embeddings found for video ID: {video_id}. "
                       "Please run the 'generate_video_descriptions_and_embeddings' endpoint first."
            )
        
        stored_descriptions = video_embeddings_store[video_id]

        # Generate embedding for the search query
        print(f"Generating embedding for search query: '{search_query}'")
        query_embedding_response = await asyncio.to_thread(
            lambda: genai.embed_content(
                model='models/embedding-001',
                content=search_query,
                task_type="RETRIEVAL_QUERY" # Recommended task type for queries
            )
        )
        query_embedding_vector = query_embedding_response['embedding']

        # Perform similarity search
        search_results = []
        for vd in stored_descriptions:
            similarity = cosine_similarity(query_embedding_vector, vd.embedding)
            search_results.append(VisualSearchResult(
                timestamp=vd.timestamp,
                description=vd.description,
                similarity_score=similarity
            ))
        
        # Sort results by similarity score in descending order
        search_results.sort(key=lambda x: x.similarity_score, reverse=True)

        # Return top N results (e.g., top 5)
        top_results = search_results[:3] # You can adjust N here

        print(f"Found {len(top_results)} visual search results for '{search_query}' in video {video_id}.")

        return VisualSearchResultsResponse(
            video_id=video_id,
            search_query=search_query,
            results=top_results
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException: # Re-raise if it's already an HTTPException
        raise
    except Exception as e:
        print(f"An unexpected error occurred during visual search: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Visual search failed: {str(e)}. Please ensure your API key is valid and embeddings were generated."
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