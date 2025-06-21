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
    </div>
  );
}