"use client";

import { useState, useEffect } from "react";

interface Timestamp {
  time: string; // Format: "MM:SS" or "HH:MM:SS"
  description: string;
  seconds: number; // Time in seconds for navigation
}

interface VideoTimestampsProps {
  videoUrl: string;
  isVisible: boolean;
  onTimestampClick?: (seconds: number) => void;
}

export function VideoTimestamps({ videoUrl, isVisible, onTimestampClick }: VideoTimestampsProps) {
  const [timestamps, setTimestamps] = useState<Timestamp[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

  // Fetch timestamps from backend when component becomes visible
  useEffect(() => {
    if (isVisible && videoUrl) {
      fetchTimestamps();
    }
  }, [isVisible, videoUrl]);

  const fetchTimestamps = async () => {
    setIsLoading(true);
    setError("");

    try {
      
      /* for Windows Users, if the port 8000 is occupied, use port 8001*/ 
      const response = await fetch("http://localhost:8001/timestamps", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ video_url: videoUrl }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      
      if (data.success && data.timestamps) {
        setTimestamps(data.timestamps);
      } else {
        throw new Error("Failed to fetch timestamps");
      }
    } catch (err: any) {
      setError(err.message || "Failed to load timestamps");
      console.error("Error fetching timestamps:", err);
    } finally {
      setIsLoading(false);
    }
  };

  const formatTime = (timeString: string) => {
    // Ensure consistent formatting for display
    const parts = timeString.split(':');
    if (parts.length === 2) {
      // MM:SS format
      return timeString;
    } else if (parts.length === 3) {
      // HH:MM:SS format
      return timeString;
    }
    return timeString;
  };

  const handleTimestampClick = (timestamp: Timestamp) => {
    // Validate timestamp before navigation
    if (timestamp.seconds < 0) {
      console.warn(`Invalid timestamp: negative seconds (${timestamp.seconds})`);
      return;
    }
    
    // Reasonable upper limit (2 hours = 7200 seconds)
    if (timestamp.seconds > 7200) {
      console.warn(`Timestamp beyond reasonable limit: ${timestamp.time} (${timestamp.seconds}s)`);
      return;
    }
    
    // Call the parent callback to navigate the video
    if (onTimestampClick) {
      onTimestampClick(timestamp.seconds);
    }
  };

  if (!isVisible) return null;

  return (
    <div className="h-full overflow-hidden bg-white/[0.03] rounded-lg border border-white/[0.1] flex flex-col">
      {/* Fixed Header */}
      <div className="flex-shrink-0 p-6 pb-4">
        <h3 className="text-lg font-medium text-white mb-2">Video Timestamps</h3>
        <p className="text-sm text-zinc-400">
          Click on any timestamp to jump to that moment in the video
        </p>
      </div>

      {/* Scrollable Content Area */}
      <div className="flex-1 overflow-hidden px-6">
        {/* Loading State */}
        {isLoading && (
          <div className="flex items-center justify-center h-full">
            <div className="flex items-center space-x-2">
              <div className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
              <span className="text-zinc-400">Loading timestamps...</span>
            </div>
          </div>
        )}

        {/* Error State */}
        {error && !isLoading && (
          <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-lg">
            <p className="text-red-400 text-sm">{error}</p>
          </div>
        )}

        {/* Timestamps List - Scrollable */}
        {!isLoading && timestamps.length > 0 && (
          <div className="h-full overflow-y-auto pr-2 pb-4 custom-scrollbar">
            <div className="space-y-3">
              {timestamps.map((timestamp, index) => (
                <div
                  key={index}
                  className="flex flex-col p-3 bg-white/[0.02] rounded-lg border border-white/[0.05] hover:bg-white/[0.05] transition-colors cursor-pointer group"
                  onClick={() => handleTimestampClick(timestamp)}
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-blue-400 hover:text-blue-300 font-mono text-sm font-medium transition-colors">
                      {formatTime(timestamp.time)}
                    </span>
                    
                    <span className="text-xs text-zinc-500">
                      #{index + 1}
                    </span>
                  </div>
                  
                  <div className="text-zinc-300 text-sm leading-relaxed break-words">
                    {timestamp.description}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Empty State */}
        {!isLoading && timestamps.length === 0 && !error && (
          <div className="flex items-center justify-center h-full">
            <p className="text-center text-zinc-500">No timestamps available for this video.</p>
          </div>
        )}
      </div>

      {/* Fixed Footer */}
      <div className="flex-shrink-0 p-6 pt-4 border-t border-white/[0.1]">
        <p className="text-xs text-zinc-500 text-center">
          {timestamps.length} timestamps available
        </p>
      </div>

      {/* Custom scrollbar styles */}
      <style jsx>{`
        .custom-scrollbar::-webkit-scrollbar {
          width: 6px;
        }
        
        .custom-scrollbar::-webkit-scrollbar-track {
          background: rgba(39, 39, 42, 0.3);
          border-radius: 3px;
        }
        
        .custom-scrollbar::-webkit-scrollbar-thumb {
          background: rgba(113, 113, 122, 0.5);
          border-radius: 3px;
        }
        
        .custom-scrollbar::-webkit-scrollbar-thumb:hover {
          background: rgba(113, 113, 122, 0.7);
        }
        
        .custom-scrollbar {
          scrollbar-width: thin;
          scrollbar-color: rgba(113, 113, 122, 0.5) rgba(39, 39, 42, 0.3);
        }
      `}</style>
    </div>
  );
}