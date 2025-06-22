"use client";

import { useState } from "react";

export function YouTubeAnalyzer() {
  const [videoUrl, setVideoUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [summary, setSummary] = useState("");
  const [error, setError] = useState("");
  
  // Chat states
  const [chatMessages, setChatMessages] = useState<Array<{role: 'user' | 'assistant', content: string}>>([]);
  const [currentQuestion, setCurrentQuestion] = useState("");
  const [chatLoading, setChatLoading] = useState(false);
  const [showChat, setShowChat] = useState(false);

  const analyzeVideo = async () => {
    // Reset states
    setLoading(true);
    setError("");
    setSummary("");
    setChatMessages([]);
    setShowChat(false);

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
        setShowChat(true); // Enable chat after successful analysis
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

  const askQuestion = async () => {
    if (!currentQuestion.trim() || !videoUrl) return;

    const userMessage = currentQuestion;
    setCurrentQuestion("");
    setChatMessages(prev => [...prev, { role: 'user', content: userMessage }]);
    setChatLoading(true);

    try {
      const response = await fetch("http://localhost:8000/ask_question", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ 
          video_url: videoUrl,
          question: userMessage 
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Failed to get answer");
      }

      if (data.success && data.answer) {
        setChatMessages(prev => [...prev, { role: 'assistant', content: data.answer }]);
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

  const formatChatMessage = (content: string) => {
    // Replace markdown links with actual links
    const linkPattern = /\[(\d{2}:\d{2})\]\((https?:\/\/[^\s)]+)\)/g;
    const parts = content.split(linkPattern);
    
    return parts.map((part, index) => {
      // Every third part starting from index 1 is a timestamp
      if (index % 3 === 1) {
        const url = parts[index + 1];
        return (
          <a
            key={index}
            href={url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-blue-400 hover:text-blue-300 underline"
          >
            {part}
          </a>
        );
      }
      // Skip URL parts
      if (index % 3 === 2) return null;
      // Regular text
      return <span key={index}>{part}</span>;
    });
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
                <div className="flex space-x-3">
                    <button
                    onClick={() => {
                        setSummary("");
                        setVideoUrl("");
                        setChatMessages([]);
                        setShowChat(false);
                    }}
                    className="text-sm text-zinc-400 hover:text-white transition-colors"
                    >
                    Clear
                    </button>
                    <button
                    onClick={async () => {
                        const encoded = encodeURIComponent(summary);
                        const response = await fetch(`http://localhost:8000/download_summary_pdf?summary=${encoded}`);
                        const blob = await response.blob();
                        const link = document.createElement('a');
                        link.href = window.URL.createObjectURL(blob);
                        link.download = "video_summary.pdf";
                        link.click();
                    }}
                    className="text-sm text-blue-400 hover:text-white underline"
                    >
                    Download PDF
                    </button>
                </div>
            </div>

          
          <div className="p-6 bg-white/[0.05] border border-white/[0.1] rounded-lg backdrop-blur-sm">
            <div className="prose prose-invert max-w-none">
              {formatSummary(summary)}
            </div>
          </div>
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