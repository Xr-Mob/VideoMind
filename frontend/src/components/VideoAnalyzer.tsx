"use client";

import { useState } from "react";

export function YouTubeAnalyzer() {
  const [videoUrl, setVideoUrl] = useState("");
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
          onClick={analyzeVideo}
          disabled={!videoUrl.trim() || loading}
          className="w-full px-6 py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-zinc-700 disabled:cursor-not-allowed text-white font-medium rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:ring-offset-zinc-900 flex items-center justify-center"
        >
          {loading ? (
            <>
              <svg 
                className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" 
                xmlns="http://www.w3.org/2000/svg" 
                fill="none" 
                viewBox="0 0 24 24"
              >
                <circle 
                  className="opacity-25" 
                  cx="12" 
                  cy="12" 
                  r="10" 
                  stroke="currentColor" 
                  strokeWidth="4"
                />
                <path 
                  className="opacity-75" 
                  fill="currentColor" 
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                />
              </svg>
              Analyzing Video...
            </>
          ) : (
            "Analyze Video"
          )}
        </button>
      </div>

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