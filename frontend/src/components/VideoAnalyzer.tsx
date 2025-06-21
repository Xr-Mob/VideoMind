"use client";

import { useState, useRef } from "react";
import { Chatbot } from "./Chatbot";
import { VideoTimestamps } from "./VideoTimestamps";
import { VideoDisplay, VideoDisplayRef } from "./VideoDisplay";

export function YouTubeAnalyzer() {
  const [videoUrl, setVideoUrl] = useState("");
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [showChatbot, setShowChatbot] = useState(false);
  const [showTimestamps, setShowTimestamps] = useState(false);
  const [showVideoDisplay, setShowVideoDisplay] = useState(false);
  const [analysisComplete, setAnalysisComplete] = useState(false);
  
  const videoDisplayRef = useRef<VideoDisplayRef>(null);

  const isValidYouTubeUrl = (url: string) => {
    const youtubeRegex = /^(https?:\/\/)?(www\.)?(youtube\.com\/watch\?v=|youtu\.be\/)[a-zA-Z0-9_-]{11}/;
    return youtubeRegex.test(url);
  };

  const handleTimestampClick = (seconds: number) => {
    // Navigate the video to the specified timestamp
    if (videoDisplayRef.current) {
      videoDisplayRef.current.navigateToTime(seconds);
    }
    console.log(`Navigating to ${seconds} seconds`);
  };

  const handleAnalyze = async () => {
    if (!videoUrl.trim() || !isValidYouTubeUrl(videoUrl)) return;

    setIsAnalyzing(true);
    setShowChatbot(false);
    setShowTimestamps(false);
    setShowVideoDisplay(false);
    setAnalysisComplete(false);

    // Comment out backend call for now - just show components immediately
    /*
    try {
      // Send the video URL to the backend for analysis
      const response = await fetch("/api/analyze", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          video_url: videoUrl,
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      console.log("Analysis complete:", data);
      
      // Show the components after successful analysis
      setAnalysisComplete(true);
      setShowChatbot(true);
      setShowTimestamps(true);
      setShowVideoDisplay(true);
    } catch (error) {
      console.error("Error analyzing video:", error);
      alert("Failed to analyze video. Please check the URL and try again.");
    } finally {
      setIsAnalyzing(false);
    }
    */

    // Simulate analysis delay and show components immediately
    setTimeout(() => {
      setAnalysisComplete(true);
      setShowChatbot(true);
      setShowTimestamps(true);
      setShowVideoDisplay(true);
      setIsAnalyzing(false);
    }, 1000);
  };
  const [loading, setLoading] = useState(false);
  const [summary, setSummary] = useState("");
  const [error, setError] = useState("");

  const analyzeVideo = async () => {
    // Reset states
    setLoading(true);
    setError("");
    setSummary("");

    try {
      const response = await fetch("http://localhost:8000/analyze_video", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ youtube_url: videoUrl }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Failed to analyze video");
      }

      if (data.success && data.video_summary) {
        setSummary(data.video_summary);
      } else {
        throw new Error("Failed to generate summary");
      }
    } catch (err: any) {
      setError(err.message || "An error occurred while analyzing the video");
      console.error("Error:", err);
    } finally {
      setLoading(false);
    }
  };

  const formatSummary = (text: string) => {
    // Split the text into sections
    const sections = text.split(/\*\*([^*]+):\*\*/g);
    
    return sections.map((section, index) => {
      // Skip empty sections
      if (!section.trim()) return null;
      
      // Check if this is a header (odd indices after split)
      if (index % 2 === 1) {
        return (
          <h3 key={index} className="text-lg font-semibold text-white mt-4 mb-2">
            {section}
          </h3>
        );
      }
      
      // Process content sections
      const lines = section.split('\n').filter(line => line.trim());
      
      return lines.map((line, lineIndex) => {
        // Check if it's a bullet point
        if (line.trim().startsWith('•')) {
          return (
            <li key={`${index}-${lineIndex}`} className="text-zinc-300 ml-4 mb-1 list-none">
              {line.trim()}
            </li>
          );
        }
        
        // Regular paragraph
        if (line.trim()) {
          return (
            <p key={`${index}-${lineIndex}`} className="text-zinc-300 mb-2">
              {line.trim()}
            </p>
          );
        }
        
        return null;
      });
    }).filter(Boolean);
  };

  return (
    <div className="space-y-6">
      <div className="space-y-4">
        <div>
          <label
            htmlFor="youtube-url"
            className="block text-sm font-medium text-zinc-300 mb-2"
          >
            YouTube Video URL
          </label>
          <input
            id="youtube-url"
            type="url"
            value={videoUrl}
            onChange={e => setVideoUrl(e.target.value)}
            placeholder="https://www.youtube.com/watch?v=..."
            className="w-full px-4 py-3 bg-white/[0.05] border border-white/[0.1] rounded-lg text-white placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
          />
        </div>

        <button
          type="button"
          disabled={!videoUrl.trim() || !isValidYouTubeUrl(videoUrl) || isAnalyzing}
          onClick={handleAnalyze}
          className="w-full px-6 py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-zinc-700 disabled:cursor-not-allowed text-white font-medium rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:ring-offset-zinc-900"
        >
          {isAnalyzing ? (
            <div className="flex items-center justify-center space-x-2">
              <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
              <span>Analyzing Video...</span>
            </div>
          ) : (
            "Analyze Video"
          )}
        </button>

        {!isValidYouTubeUrl(videoUrl) && videoUrl.trim() && (
          <p className="text-red-400 text-sm">
            Please enter a valid YouTube video URL
          </p>
        )}
      </div>

      {/* Video Display Section */}
      {showVideoDisplay && analysisComplete && (
        <div className="mt-8">
          <VideoDisplay 
            ref={videoDisplayRef}
            videoUrl={videoUrl} 
            isVisible={showVideoDisplay}
            onTimestampClick={handleTimestampClick}
          />
        </div>
      )}

      {/* Video Timestamps Section */}
      {showTimestamps && analysisComplete && (
        <div className="mt-8">
          <VideoTimestamps 
            videoUrl={videoUrl} 
            isVisible={showTimestamps}
            onTimestampClick={handleTimestampClick}
          />
        </div>
      )}

      {/* Chatbot Section */}
      {showChatbot && analysisComplete && (
        <div className="mt-8">
          <Chatbot videoUrl={videoUrl} isVisible={showChatbot} />
        </div>
      )}

      {/* Error Message */}
      {error && (
        <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-lg">
          <div className="flex items-start space-x-3">
            <svg 
              className="w-5 h-5 text-red-400 mt-0.5" 
              fill="none" 
              stroke="currentColor" 
              viewBox="0 0 24 24"
            >
              <path 
                strokeLinecap="round" 
                strokeLinejoin="round" 
                strokeWidth={2} 
                d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" 
              />
            </svg>
            <p className="text-red-400">{error}</p>
          </div>
        </div>
      )}

      {/* Summary Display */}
      {summary && !loading && (
        <div className="space-y-4 animate-fadeIn">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-semibold text-white">Video Summary</h2>
            <button
              onClick={() => {
                setSummary("");
                setVideoUrl("");
              }}
              className="text-sm text-zinc-400 hover:text-white transition-colors"
            >
              Clear
            </button>
          </div>
          
          <div className="p-6 bg-white/[0.05] border border-white/[0.1] rounded-lg backdrop-blur-sm">
            <div className="prose prose-invert max-w-none">
              {formatSummary(summary)}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}