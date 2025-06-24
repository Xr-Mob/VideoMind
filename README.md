# VideoMind

A web application that analyzes YouTube videos and allows users to ask questions about the video content through a chatbot interface.

## Authors

- Kevin Binu Thottumkal
- Jeesmon Cherian
- Desmond Zhu

## Features

- **YouTube Video Analysis**: Paste a YouTube URL to analyze video content
- **AI Chatbot**: Ask natural language questions about the analyzed video
- **Video Timestamps**: Navigate through key moments in the video
- **Video Player**: Embedded YouTube player with timestamp navigation
- **Modern UI**: Beautiful, responsive interface built with Next.js and Tailwind CSS
- **FastAPI Backend**: Scalable backend for video processing and AI interactions

## Project Structure

```
VideoMind-AI/
├── frontend/                       # Next.js frontend application
│   ├── src/
│   │   ├── app/                    # Next.js app router
│   │   └── components/             # React components
│   │       ├── VideoAnalyzer.tsx
│   │       ├── VideoDisplay.tsx
│   │       ├── VideoTimestamps.tsx
│   │       └── Chatbot.tsx
│   ├── public/                     # Static assets (icons, images)
│   ├── package.json                # Frontend dependencies
│   ├── tsconfig.json               # TypeScript config
│   └── ...
├── backend/                        # FastAPI backend application
│   ├── main.py                     # Main FastAPI application
│   ├── pdf_generator.py            # PDF generation logic
│   ├── requirements.txt            # Python dependencies
│   ├── setup.bat                   # Windows setup script
│   ├── setup.sh                    # Unix/Linux setup script
│   ├── generated_pdfs/             # Temporary PDF storage
│   └── README.md                   # Backend documentation
├── videomind_chrome_extension/     # Chrome extension for VideoMind
│   ├── manifest.json               # Chrome extension manifest
│   ├── content.js                  # Content script
│   ├── background.js               # Background script
│   ├── content.css                 # Extension styles
│   ├── icon16.png                  # Extension icon (16x16)
│   ├── icon48.png                  # Extension icon (48x48)
│   └── icon128.png                 # Extension icon (128x128)
├── .gitignore
├── README.md
└── package-lock.json
```

## Quick Start

### Backend Setup

1. **Navigate to backend directory:**
   ```bash
   cd backend
   ```

2. **Create environment file:**
   Create a `.env` file in the backend directory:
   ```env
   GEMINI_API_KEY=your_gemini_api_key_here
   ```
   
   Get your Gemini API key from: https://makersuite.google.com/app/apikey

3. **Create the virtual machine to download the dependencies in:**
     ```bash
     python -m venv venv
     ```

4. **Activate the virtual machine:**
   ```bash
   venv\Scripts\activate.bat  # Windows
   source venv/bin/activate   # Unix/Linux
   

5. **Download dependencies:**
```bash
pip install -r requirements.txt 
```

6. **Start the server:**
```bash
python main.py
```

The backend will be available at `http://localhost:8001`

### Frontend Setup

1. **Navigate to frontend directory:**
   ```bash
   cd frontend
   ```

2. **Install dependencies:**
   ```bash
   npm install
   ```

3. **Start the development server:**
   ```bash
   npm run dev
   ```

The frontend will be available at `http://localhost:3000`

## API Endpoints

### Backend Endpoints

- `POST /analyze_video` - Analyze a YouTube video and generate summary
- `POST /chat` - Process chat queries about a video
- `POST /timestamps` - Generate navigable timestamps for a video
- `GET /health` - Health check endpoint

### Frontend Components

- **VideoAnalyzer**: Handles YouTube URL input, validation, and analysis workflow
- **VideoDisplay**: Embedded YouTube player with timestamp navigation
- **VideoTimestamps**: Displays clickable timestamps for video navigation
- **Chatbot**: AI-powered chat interface for video questions

## Usage

1. Open the application in your browser at `http://localhost:3000`
2. Paste a valid YouTube video URL in the input field
3. Click "Analyze Video" to process the video
4. View the generated summary, video player, and timestamps
5. Ask questions about the video content using the chatbot
6. Click timestamps to navigate to specific moments in the video

## Technology Stack

### Frontend
- **Next.js 14** - React framework with app router
- **TypeScript** - Type-safe JavaScript
- **Tailwind CSS** - Utility-first CSS framework
- **React Hooks** - State management and side effects

### Backend
- **FastAPI** - Modern Python web framework
- **Google Gemini AI** - AI-powered video analysis and chat
- **YouTube Transcript API** - Video transcript extraction
- **Pydantic** - Data validation and serialization
- **Uvicorn** - ASGI server

## Troubleshooting

### Common Issues

1. **"uvicorn not recognized" error:**
   - Make sure you've run the setup script and activated the virtual environment
   - Try: `pip install uvicorn[standard]`

2. **CORS errors:**
   - Ensure the backend is running on `http://localhost:8001`
   - Check that CORS is properly configured in the backend

3. **API key errors:**
   - Verify your Gemini API key is correctly set in the `.env` file
   - Check that the API key is valid and has sufficient quota

4. **Video analysis fails:**
   - Ensure the YouTube video has captions/transcripts enabled
   - Check that the video URL is valid and accessible

### Development

- **Backend logs**: Check the terminal where the backend is running
- **Frontend logs**: Check the browser console (F12)
- **Network issues**: Use browser dev tools to inspect API requests
