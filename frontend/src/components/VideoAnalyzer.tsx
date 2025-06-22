"use client";

import { useState, useRef } from "react";
import { VideoTimestamps } from "./VideoTimestamps";
import { VideoDisplay, VideoDisplayRef } from "./VideoDisplay";

interface SummaryTimestamp {
  time: string;
  description: string;
  seconds: number;
  text_position: number;
}

export function YouTubeAnalyzer() {
  const [videoUrl, setVideoUrl] = useState("");
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [showTimestamps, setShowTimestamps] = useState(false);
  const [showVideoDisplay, setShowVideoDisplay] = useState(false);
  const [analysisComplete, setAnalysisComplete] = useState(false);
  const [summary, setSummary] = useState("");
  const [summaryTimestamps, setSummaryTimestamps] = useState<SummaryTimestamp[]>([]);
  const [error, setError] = useState("");

  // Chat states
  const [chatMessages, setChatMessages] = useState<Array<{role: 'user' | 'assistant', content: string}>>([]);
  const [currentQuestion, setCurrentQuestion] = useState("");
  const [chatLoading, setChatLoading] = useState(false);
  const [showChat, setShowChat] = useState(false);

  const [videoDisplayReady, setVideoDisplayReady] = useState(false);
  
  const videoDisplayRef = useRef<VideoDisplayRef>(null);

  const isValidYouTubeUrl = (url: string) => {
    const youtubeRegex = /^(https?:\/\/)?(www\.)?(youtube\.com\/watch\?v=|youtu\.be\/)[a-zA-Z0-9_-]{11}/;
    return youtubeRegex.test(url);
  };

  const handleTimestampClick = (seconds: number) => {
    console.log(`Timestamp click: ${seconds} seconds, videoDisplayReady: ${videoDisplayReady}`);
    
    // Navigate the video to the specified timestamp
    if (videoDisplayRef.current && videoDisplayReady) {
      try {
        videoDisplayRef.current.navigateToTime(seconds);
        console.log(`Successfully navigated to ${seconds} seconds`);
      } catch (error) {
        console.error(`Error navigating to ${seconds} seconds:`, error);
      }
    } else {
      console.warn(`VideoDisplay not ready. videoDisplayRef.current: ${!!videoDisplayRef.current}, videoDisplayReady: ${videoDisplayReady}`);
      // Try to set the video display as ready and retry
      if (videoDisplayRef.current) {
        setVideoDisplayReady(true);
        // Retry after a short delay
        setTimeout(() => {
          if (videoDisplayRef.current) {
            try {
              videoDisplayRef.current.navigateToTime(seconds);
              console.log(`Retry successful: navigated to ${seconds} seconds`);
            } catch (error) {
              console.error(`Retry failed: Error navigating to ${seconds} seconds:`, error);
            }
          }
        }, 100);
      }
    }
  };

  const handleAnalyze = async () => {
    if (!videoUrl.trim() || !isValidYouTubeUrl(videoUrl)) return;

    // Reset states
    setIsAnalyzing(true);
    setError("");
    setSummary("");
    setSummaryTimestamps([]);
    setShowTimestamps(false);
    setShowVideoDisplay(false);
    setAnalysisComplete(false);
    setVideoDisplayReady(false);
    setChatMessages([]);
    setShowChat(false);

    try {
      const response = await fetch("http://localhost:8001/analyze_video", {
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
        setSummaryTimestamps(data.summary_timestamps || []);
        setAnalysisComplete(true);
        setShowTimestamps(true);
        setShowVideoDisplay(true);
        setShowChat(true); // Enable chat after successful analysis
      } else {
        throw new Error("Failed to generate summary");
      }
    } catch (err: any) {
      setError(err.message || "An error occurred while analyzing the video");
      console.error("Error:", err);
    } finally {
      setIsAnalyzing(false);
    }
  };

  const askQuestion = async () => {
    if (!currentQuestion.trim() || !videoUrl) return;

    const userMessage = currentQuestion;
    setCurrentQuestion("");
    setChatMessages(prev => [...prev, { role: 'user', content: userMessage }]);
    setChatLoading(true);

    try {
      const response = await fetch("http://localhost:8001/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ 
          video_url: videoUrl,
          query: userMessage 
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Failed to get answer");
      }

      if (data.success && data.response) {
        setChatMessages(prev => [...prev, { role: 'assistant', content: data.response }]);
      } else {
        throw new Error("Failed to get answer");
      }
    } catch (err: any) {
      setChatMessages(prev => [...prev, { 
        role: 'assistant', 
        content: `Sorry, I couldn't answer that question. ${err.message}` 
      }]);
    } finally {
      setChatLoading(false);
    }
  };

  const formatSummaryWithClickableTimestamps = (text: string, timestamps: SummaryTimestamp[]) => {
    // If no timestamps, just use the basic formatSummary
    if (!timestamps || timestamps.length === 0) {
      return formatSummary(text);
    }

    // Sort timestamps by position in descending order to replace from end to start
    const sortedTimestamps = [...timestamps].sort((a, b) => b.text_position - a.text_position);
    
    let processedText = text;
    
    // Replace each timestamp with a placeholder
    sortedTimestamps.forEach((timestamp, index) => {
      // Pattern to match timestamps at the end of summary points: "description. [1:30]"
      const timePattern = new RegExp(`(\\s*\\[${timestamp.time.replace(/:/g, '\\:')}\\]\\s*)`, 'g');
      
      processedText = processedText.replace(timePattern, (match) => {
        return `__TIMESTAMP_${index}__`;
      });
    });

    // Split the text and create React elements
    const parts = processedText.split(/(__TIMESTAMP_\d+__)/);
    
    const elements = [];
    for (let index = 0; index < parts.length; index++) {
      const part = parts[index];
      const timestampMatch = part.match(/__TIMESTAMP_(\d+)__/);
      
      if (timestampMatch) {
        const timestampIndex = parseInt(timestampMatch[1]);
        const timestamp = sortedTimestamps[timestampIndex];
        
        elements.push(
          <span
            key={`timestamp-${timestampIndex}-${index}`}
            onClick={() => handleTimestampClick(timestamp.seconds)}
            className="text-blue-400 hover:text-blue-300 font-mono font-medium transition-colors cursor-pointer underline ml-1"
            title={`Jump to ${timestamp.time} - ${timestamp.description}`}
          >
            [{timestamp.time}]
          </span>
        );
      } else if (part.trim()) {
        // Process regular text with formatting - only if part is not empty
        const textElements = formatSummaryText(part, `text-${index}`);
        // Add a wrapper div with key to contain the text elements
        elements.push(
          <div key={`text-wrapper-${index}`}>
            {textElements}
          </div>
        );
      }
    }
    
    return <>{elements}</>;
  };

  const formatSummaryText = (text: string, key: string) => {
    // Split the text into sections
    const sections = text.split(/\*\*([^*]+):\*\*/g);
    
    const elements = [];
    for (let index = 0; index < sections.length; index++) {
      const section = sections[index];
      
      // Skip empty sections
      if (!section.trim()) continue;
      
      // Check if this is a header (odd indices after split)
      if (index % 2 === 1) {
        elements.push(
          <h3 key={`${key}-header-${index}`} className="text-lg font-semibold text-white mt-4 mb-2">
            {section}
          </h3>
        );
        continue;
      }
      
      // Process content sections
      const lines = section.split('\n').filter(line => line.trim());
      const lineElements = [];
      
      for (let lineIndex = 0; lineIndex < lines.length; lineIndex++) {
        const line = lines[lineIndex];
        
        // Check if it's a bullet point
        if (line.trim().startsWith('•')) {
          lineElements.push(
            <div key={`${key}-${index}-${lineIndex}`} className="text-zinc-300 ml-4 mb-1">
              {line.trim()}
            </div>
          );
        }
        // Regular paragraph
        else if (line.trim()) {
          lineElements.push(
            <p key={`${key}-${index}-${lineIndex}`} className="text-zinc-300 mb-2">
              {line.trim()}
            </p>
          );
        }
      }
      
      if (lineElements.length > 0) {
        elements.push(
          <div key={`${key}-section-${index}`}>
            {lineElements}
          </div>
        );
      }
    }
    
    return <>{elements}</>;
  };

  const formatSummary = (text: string) => {
    // Split the text into sections
    const sections = text.split(/\*\*([^*]+):\*\*/g);
    
    const elements = [];
    for (let index = 0; index < sections.length; index++) {
      const section = sections[index];
      
      // Skip empty sections
      if (!section.trim()) continue;
      
      // Check if this is a header (odd indices after split)
      if (index % 2 === 1) {
        elements.push(
          <h3 key={`summary-header-${index}`} className="text-lg font-semibold text-white mt-4 mb-2">
            {section}
          </h3>
        );
        continue;
      }
      
      // Process content sections
      const lines = section.split('\n').filter(line => line.trim());
      const lineElements = [];
      
      for (let lineIndex = 0; lineIndex < lines.length; lineIndex++) {
        const line = lines[lineIndex];
        
        // Check if it's a bullet point
        if (line.trim().startsWith('•')) {
          lineElements.push(
            <div key={`summary-${index}-${lineIndex}`} className="text-zinc-300 ml-4 mb-1">
              {line.trim()}
            </div>
          );
        }
        // Regular paragraph
        else if (line.trim()) {
          lineElements.push(
            <p key={`summary-${index}-${lineIndex}`} className="text-zinc-300 mb-2">
              {line.trim()}
            </p>
          );
        }
      }
      
      if (lineElements.length > 0) {
        elements.push(
          <div key={`summary-section-${index}`}>
            {lineElements}
          </div>
        );
      }
    }
    
    return <>{elements}</>;
  };

  const formatChatMessage = (content: string) => {
    // Replace markdown links with actual links
    const linkPattern = /\[(\d{2}:\d{2})\]\((https?:\/\/[^\s)]+)\)/g;
    const parts = content.split(linkPattern);
    
    const elements = [];
    for (let index = 0; index < parts.length; index++) {
      const part = parts[index];
      
      // Every third part starting from index 1 is a timestamp
      if (index % 3 === 1) {
        const url = parts[index + 1];
        elements.push(
          <a
            key={`link-${index}`}
            href={url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-blue-400 hover:text-blue-300 underline"
          >
            {part}
          </a>
        );
      }
      // Skip URL parts (index % 3 === 2)
      else if (index % 3 === 2) {
        continue; // Skip URL parts
      }
      // Regular text (index % 3 === 0)
      else {
        elements.push(<span key={`text-${index}`}>{part}</span>);
      }
    }
    
    return elements;
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
          className="w-full px-6 py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-500 disabled:cursor-not-allowed text-white font-medium rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:ring-offset-zinc-900"
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

      {/* Video Display and Timestamps Section - Side by Side */}
      {(showVideoDisplay || showTimestamps) && analysisComplete && (
        <div className="mt-8">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start lg:h-[600px]">
            {/* Video Player - Takes 2/3 of the width */}
            <div className="lg:col-span-2 h-full">
              <VideoDisplay 
                ref={videoDisplayRef}
                videoUrl={videoUrl} 
                isVisible={showVideoDisplay}
                onReady={() => setVideoDisplayReady(true)}
              />
            </div>
            
            {/* Video Timestamps - Takes 1/3 of the width */}
            <div className="lg:col-span-1 h-full">
              <VideoTimestamps 
                videoUrl={videoUrl} 
                isVisible={showTimestamps}
                onTimestampClick={handleTimestampClick}
              />
            </div>
          </div>
        </div>
      )}

      {/* Summary Display - Now under the video player with clickable timestamps */}
      {summary && !isAnalyzing && (
        <div className="space-y-4 animate-fadeIn">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-semibold text-white">Video Summary</h2>
            <button
              onClick={() => {
                setSummary("");
                setSummaryTimestamps([]);
                setVideoUrl("");
                setShowTimestamps(false);
                setShowVideoDisplay(false);
                setAnalysisComplete(false);
                setChatMessages([]);
                setShowChat(false);
              }}
              className="text-sm text-zinc-400 hover:text-white transition-colors"
            >
              Clear
            </button>
          </div>
          
          <div className="p-6 bg-white/[0.05] border border-white/[0.1] rounded-lg backdrop-blur-sm">
            <div className="prose prose-invert max-w-none">
              {summaryTimestamps && summaryTimestamps.length > 0 
                ? formatSummaryWithClickableTimestamps(summary, summaryTimestamps)
                : formatSummary(summary)
              }
            </div>
          </div>
          
          {summaryTimestamps.length > 0 && (
            <div className="text-xs text-zinc-500 text-center">
              💡 Click on any timestamp in the summary to jump to that moment in the video
            </div>
          )}
        </div>
      )}

      {/* Chat Section */}
      {showChat && summary && (
        <div className="space-y-4 animate-fadeIn">
          <div className="flex items-center space-x-2">
            <h2 className="text-xl font-semibold text-white">Ask Questions About the Video</h2>
            <svg 
              className="w-5 h-5 text-zinc-400" 
              fill="none" 
              stroke="currentColor" 
              viewBox="0 0 24 24"
            >
              <path 
                strokeLinecap="round" 
                strokeLinejoin="round" 
                strokeWidth={2} 
                d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" 
              />
            </svg>
          </div>
          
          <div className="bg-white/[0.05] border border-white/[0.1] rounded-lg backdrop-blur-sm">
            {/* Chat Messages */}
            <div className="max-h-96 overflow-y-auto p-6 space-y-4">
              {chatMessages.length === 0 ? (
                <p className="text-zinc-400 text-center py-8">
                  Ask any question about the video content. I'll try to answer with relevant timestamps!
                </p>
              ) : (
                chatMessages.map((message, index) => (
                  <div
                    key={index}
                    className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
                  >
                    <div
                      className={`max-w-[80%] rounded-lg px-4 py-2 ${
                        message.role === 'user'
                          ? 'bg-blue-600 text-white'
                          : 'bg-zinc-700 text-zinc-100'
                      }`}
                    >
                      {message.role === 'user' ? (
                        <p>{message.content}</p>
                      ) : (
                        <p>{formatChatMessage(message.content)}</p>
                      )}
                    </div>
                  </div>
                ))
              )}
              {chatLoading && (
                <div className="flex justify-start">
                  <div className="bg-zinc-700 text-zinc-100 rounded-lg px-4 py-2">
                    <div className="flex space-x-2">
                      <div className="w-2 h-2 bg-zinc-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                      <div className="w-2 h-2 bg-zinc-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                      <div className="w-2 h-2 bg-zinc-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                    </div>
                  </div>
                </div>
              )}
            </div>
            
            {/* Chat Input */}
            <div className="border-t border-white/[0.1] p-4">
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  askQuestion();
                }}
                className="flex space-x-3"
              >
                <input
                  type="text"
                  value={currentQuestion}
                  onChange={(e) => setCurrentQuestion(e.target.value)}
                  placeholder="Ask a question about the video..."
                  disabled={chatLoading}
                  className="flex-1 px-4 py-2 bg-white/[0.05] border border-white/[0.1] rounded-lg text-white placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all disabled:opacity-50"
                />
                <button
                  type="submit"
                  disabled={!currentQuestion.trim() || chatLoading}
                  className="px-6 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-zinc-700 disabled:cursor-not-allowed text-white font-medium rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  Send
                </button>
              </form>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}