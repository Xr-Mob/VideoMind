import asyncio
import json
import numpy as np
from pydantic import BaseModel, Field
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import google.generativeai as genai
import os
import re
from dotenv import load_dotenv
from youtube_transcript_api import YouTubeTranscriptApi
from urllib.parse import urlparse, parse_qs
import re

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

class QuestionRequest(BaseModel):
    video_url: str
    question: str

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

async def get_video_transcript(video_id: str) -> str:
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

async def get_video_transcript_with_timestamps(video_id: str) -> list[dict]:
    """Fetch transcript with timestamps from YouTube"""
    try:
        # Get transcript with timestamps
        transcript_list = await asyncio.to_thread(
            YouTubeTranscriptApi.get_transcript, video_id
        )
        return transcript_list
    except Exception as e:
        print(f"Error fetching transcript: {e}")
        return []

async def generate_video_summary(transcript: str, video_url: str) -> str:
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
        
        Example JSON structure:
        [
            {
                "timestamp": 10,
                "description": "A wide shot of a cityscape with towering skyscrapers under a clear blue sky."
            },
            {
                "timestamp": 45,
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