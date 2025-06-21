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
      const response = await fetch("http://localhost:8000/timestamps", {
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
      
      // Fallback to mock data if backend fails
      setTimestamps(getMockTimestamps());
    } finally {
      setIsLoading(false);
    }
  };

  // Mock data fallback - comment out when backend is fully implemented
  const getMockTimestamps = (): Timestamp[] => [
    {
      time: "00:00",
      description: "Introduction to the video",
      seconds: 0
    },
    {
      time: "00:15",
      description: "Main topic discussion begins",
      seconds: 15
    },
    {
      time: "01:30",
      description: "Key concept explanation",
      seconds: 90
    },
    {
      time: "03:45",
      description: "Practical example demonstration",
      seconds: 225
    },
    {
      time: "05:20",
      description: "Important insights shared",
      seconds: 320
    },
    {
      time: "07:10",
      description: "Conclusion and summary",
      seconds: 430
    }
  ];

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
    // Call the parent callback to navigate the video
    if (onTimestampClick) {
      onTimestampClick(timestamp.seconds);
    }
  };

  if (!isVisible) return null;

  return (
    <div className="bg-white/[0.03] rounded-lg border border-white/[0.1] p-6">
      <div className="mb-4">
        <h3 className="text-lg font-medium text-white mb-2">Video Timestamps</h3>
        <p className="text-sm text-zinc-400">
          Click on any timestamp to jump to that moment in the video
        </p>
      </div>

      {/* Loading State */}
      {isLoading && (
        <div className="flex items-center justify-center py-8">
          <div className="flex items-center space-x-2">
            <div className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
            <span className="text-zinc-400">Loading timestamps...</span>
          </div>
        </div>
      )}

      {/* Error State */}
      {error && !isLoading && (
        <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-lg mb-4">
          <p className="text-red-400 text-sm">{error}</p>
        </div>
      )}

      {/* Timestamps List */}
      {!isLoading && timestamps.length > 0 && (
        <div className="space-y-3">
          {timestamps.map((timestamp, index) => (
            <div
              key={index}
              className="flex items-center justify-between p-3 bg-white/[0.02] rounded-lg border border-white/[0.05] hover:bg-white/[0.05] transition-colors cursor-pointer"
              onClick={() => handleTimestampClick(timestamp)}
            >
              <div className="flex items-center space-x-4">
                <button
                  className="text-blue-400 hover:text-blue-300 font-mono text-sm font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:ring-offset-zinc-900 rounded px-2 py-1"
                >
                  {formatTime(timestamp.time)}
                </button>
                <span className="text-zinc-300 text-sm">
                  {timestamp.description}
                </span>
              </div>
              
              <div className="flex items-center space-x-2">
                <span className="text-xs text-zinc-500">
                  #{index + 1}
                </span>
                <svg 
                  className="w-4 h-4 text-zinc-500" 
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
            </div>
          ))}
        </div>
      )}

      {/* Empty State */}
      {!isLoading && timestamps.length === 0 && !error && (
        <div className="text-center text-zinc-500 py-8">
          <p>No timestamps available for this video.</p>
        </div>
      )}

      <div className="mt-4 pt-4 border-t border-white/[0.1]">
        <p className="text-xs text-zinc-500 text-center">
          {timestamps.length} timestamps available • Click to navigate within video
        </p>
      </div>
    </div>
  );
} 