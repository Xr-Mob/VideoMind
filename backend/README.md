# VideoMind AI Backend

FastAPI backend for video analysis and chat functionality using Google Gemini AI.

## Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Environment Configuration

Create a `.env` file in the backend directory with the following variables:

```env
# Gemini AI API Key
# Get your API key from: https://makersuite.google.com/app/apikey
GEMINI_API_KEY=your_gemini_api_key_here

# Backend Configuration
HOST=0.0.0.0
PORT=8001

# CORS Settings
ALLOWED_ORIGINS=http://localhost:3000,http://localhost
```

### 3. Run the Backend

```bash
python main.py
```

Or using uvicorn directly:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## API Endpoints

### POST `/analyze_video`
Analyzes a YouTube video and generates a summary.

**Request:**
```json
{
  "youtube_url": "https://www.youtube.com/watch?v=VIDEO_ID"
}
```

**Response:**
```json
{
  "success": true,
  "video_url": "https://www.youtube.com/watch?v=VIDEO_ID",
  "video_id": "VIDEO_ID",
  "video_summary": "Generated summary...",
  "has_transcript": true
}
```

### POST `/chat`
Processes chat queries about a video.

**Request:**
```json
{
  "video_url": "https://www.youtube.com/watch?v=VIDEO_ID",
  "query": "What is this video about?"
}
```

**Response:**
```json
{
  "success": true,
  "response": "AI-generated response based on video content..."
}
```

### POST `/timestamps`
Generates timestamps for a video.

**Request:**
```json
{
  "video_url": "https://www.youtube.com/watch?v=VIDEO_ID"
}
```

**Response:**
```json
{
  "success": true,
  "timestamps": [
    {
      "time": "00:00",
      "description": "Introduction",
      "seconds": 0
    }
  ]
}
```

### GET `/health`
Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "api_key_configured": true
}
```

## Features

- **YouTube Video Analysis**: Extracts transcripts and generates summaries
- **AI Chat**: Answers questions about video content using Gemini AI
- **Timestamp Generation**: Creates navigable timestamps for videos
- **CORS Support**: Configured for frontend integration
- **Error Handling**: Comprehensive error handling and validation

## Dependencies

- **FastAPI**: Web framework
- **Google Generative AI**: For AI-powered responses
- **YouTube Transcript API**: For extracting video transcripts
- **Pydantic**: Data validation
- **Python-dotenv**: Environment variable management

## Notes

- Requires a valid Gemini API key
- Videos must have captions/transcripts available
- Rate limiting may apply based on Gemini API quotas 