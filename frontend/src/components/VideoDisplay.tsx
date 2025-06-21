"use client";

import { useRef, useImperativeHandle, forwardRef } from "react";

interface VideoDisplayProps {
  videoUrl: string;
  isVisible: boolean;
  onTimestampClick?: (seconds: number) => void;
}

export interface VideoDisplayRef {
  navigateToTime: (seconds: number) => void;
}

export const VideoDisplay = forwardRef<VideoDisplayRef, VideoDisplayProps>(
  ({ videoUrl, isVisible, onTimestampClick }, ref) => {
    const iframeRef = useRef<HTMLIFrameElement>(null);

    const extractVideoId = (url: string): string | null => {
      const regex = /(?:youtube\.com\/watch\?v=|youtu\.be\/)([a-zA-Z0-9_-]{11})/;
      const match = url.match(regex);
      return match ? match[1] : null;
    };

    const navigateToTime = (seconds: number) => {
      if (iframeRef.current) {
        const videoId = extractVideoId(videoUrl);
        if (videoId) {
          // Update the iframe src with the new timestamp
          const newUrl = `https://www.youtube.com/embed/${videoId}?start=${seconds}&autoplay=1&rel=0&modestbranding=1`;
          iframeRef.current.src = newUrl;
        }
      }
      
      // Also call the parent callback if provided
      if (onTimestampClick) {
        onTimestampClick(seconds);
      }
    };

    // Expose the navigateToTime function to parent components
    useImperativeHandle(ref, () => ({
      navigateToTime
    }));

    const videoId = extractVideoId(videoUrl);
    const embedUrl = videoId 
      ? `https://www.youtube.com/embed/${videoId}?rel=0&modestbranding=1`
      : "";

    if (!isVisible || !videoId) return null;

    return (
      <div className="bg-white/[0.03] rounded-lg border border-white/[0.1] p-6">
        <div className="mb-4">
          <h3 className="text-lg font-medium text-white mb-2">Video Player</h3>
          <p className="text-sm text-zinc-400">
            Watch the video and use timestamps below to navigate
          </p>
        </div>

        <div className="relative w-full">
          <div className="aspect-video w-full">
            <iframe
              ref={iframeRef}
              src={embedUrl}
              title="YouTube video player"
              className="w-full h-full rounded-lg"
              frameBorder="0"
              allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
              allowFullScreen
            />
          </div>
        </div>

        <div className="mt-4 flex items-center justify-between text-sm text-zinc-400">
          <span>Video ID: {videoId}</span>
          <span>Click timestamps to navigate</span>
        </div>
      </div>
    );
  }
);

VideoDisplay.displayName = "VideoDisplay"; 