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

# Request model
class UrlAnalyzeRequest(BaseModel):
    youtube_url: str

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