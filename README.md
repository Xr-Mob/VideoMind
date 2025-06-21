# VideoMind AI

A web application that analyzes YouTube videos and allows users to ask questions about the video content through a chatbot interface.

## Features

- **YouTube Video Analysis**: Paste a YouTube URL to analyze video content
- **AI Chatbot**: Ask natural language questions about the analyzed video
- **Modern UI**: Beautiful, responsive interface built with Next.js and Tailwind CSS
- **FastAPI Backend**: Scalable backend for video processing and AI interactions

## Project Structure

```
VideoMind-AI/
├── frontend/                 # Next.js frontend application
│   ├── src/
│   │   ├── app/             # Next.js app router
│   │   │   ├── api/         # API routes for backend communication
│   │   │   └── ...
│   │   └── components/      # React components
│   │       ├── VideoAnalyzer.tsx
│   │       └── Chatbot.tsx
│   └── ...
├── backend/                  # FastAPI backend application
│   ├── main.py              # Main FastAPI application
│   └── requirements.txt     # Python dependencies
└── README.md
```

## Setup Instructions

### Frontend Setup

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Create a `.env.local` file in the frontend directory:
   ```env
   FASTAPI_BASE_URL=http://localhost:8000
   ```

4. Start the development server:
   ```bash
   npm run dev
   ```

The frontend will be available at `http://localhost:3000`

### Backend Setup

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Create a virtual environment (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Start the FastAPI server:
   ```bash
   python main.py
   ```

The backend will be available at `http://localhost:8000`

## API Endpoints

### Backend Endpoints

- `POST /analyze` - Analyze a YouTube video
  - Request: `{"video_url": "https://www.youtube.com/watch?v=..."}`
  - Response: `{"success": true, "message": "...", "video_id": "...", "title": "...", "duration": "..."}`

- `POST /chat` - Chat with video content
  - Request: `{"video_url": "...", "query": "What is this video about?"}`
  - Response: `{"response": "...", "success": true}`

- `GET /health` - Health check endpoint

### Frontend API Routes

- `POST /api/analyze` - Proxies to backend `/analyze` endpoint
- `POST /api/chat` - Proxies to backend `/chat` endpoint

## Usage

1. Open the application in your browser at `http://localhost:3000`
2. Paste a valid YouTube video URL in the input field
3. Click "Analyze Video" to process the video
4. Once analysis is complete, the chatbot will appear
5. Ask questions about the video content using natural language

## Implementation Notes

### Frontend Components

- **VideoAnalyzer**: Handles YouTube URL input and validation, triggers video analysis
- **Chatbot**: Manages chat interface, sends queries to backend, displays responses

### Backend Implementation

The current backend provides placeholder implementations. To make it fully functional, you'll need to:

1. **Video Processing**: Implement actual video download and processing using libraries like `yt-dlp`
2. **Audio Transcription**: Use Whisper or similar for speech-to-text conversion
3. **AI Integration**: Connect to LLM services (OpenAI, Anthropic, etc.) for intelligent responses
4. **Data Storage**: Implement database storage for processed video data
5. **Caching**: Add Redis or similar for caching analysis results

### Environment Variables

- `FASTAPI_BASE_URL`: URL of the FastAPI backend (default: `http://localhost:8000`)

## Development

### Adding New Features

1. **Frontend**: Add new components in `frontend/src/components/`
2. **Backend**: Add new endpoints in `backend/main.py`
3. **API Routes**: Create corresponding Next.js API routes in `frontend/src/app/api/`

### Styling

The application uses Tailwind CSS for styling. All components follow a dark theme with blue accents.

## Troubleshooting

- **CORS Issues**: Ensure the backend CORS settings include your frontend URL
- **API Connection**: Check that `FASTAPI_BASE_URL` is correctly set
- **Port Conflicts**: Make sure ports 3000 (frontend) and 8000 (backend) are available

## License

This project is open source and available under the MIT License. 