'''
    This is the python backend using FAST API to process youtuve watch URLs with the help of Gemini AI
    
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

GEMINI_MODEL_FOR_VIDEO = 'models/gemini-2.0-flash'

#Make sure the backend folder has .env folder with the gemini api key. Else replace the os.getenv() with gemini key directly :)
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel(GEMINI_MODEL_FOR_VIDEO)

app = FastAPI(
    title= "VIDEOMIND-AI",
    description= "API for mutlimodal video analysis",
    version="1.0.0"
)

#Allows Cors
app.add_middleware(
    CORSMiddleware,
    allow_origins= ["http://localhost","http://localhost:3000"],
    allow_credentials= True,
    allow_methods= ["*"],
    allow_headers=["*"]
)

#Post model
class UrlAnalyzeRequest(BaseModel):
    youtube_url: str

@app.post("/analyze_video")
async def analyze_youtube_video(request_data: UrlAnalyzeRequest):

    youtube_url_string = request_data.youtube_url # Extract the actual URL string from the Pydantic model

    if not youtube_url_string.startswith("http") or "youtube.com/watch?v=" not in youtube_url_string:
        raise HTTPException(status_code=400, detail="Invalid YouTube URL format provided.")

    try:
        print(f"Sending video '{youtube_url_string}' to {GEMINI_MODEL_FOR_VIDEO} for analysis...")
        response = await asyncio.to_thread(
            lambda: model.generate_content(
                contents=[
                    {
                        "file_data": {
                            "file_uri": youtube_url_string,
                            "mime_type": "video/mp4" # Specify the MIME type
                        }
                    },
                    {"text": "Please summarize this video in 3 sentences and identify any key objects or actions visible."}
                ]
            )
        ) 

        print("\n--- Gemini AI Response ---")
        print(response.text)
        print("--------------------------")
        return {"video_summary" : response.text} # response json

    except Exception as e:
        print(f"An error occurred during video analysis: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Video analysis failed: {e}. Please ensure your API key is correct, the video URL is valid and publicly accessible, and the model ('{GEMINI_MODEL_FOR_VIDEO}') is available for your project."
        )
    
@app.get("/")
async def read_root():
    return {"message": "VIDEOMIND-AI backend is running!"}