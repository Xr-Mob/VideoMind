"use client";

import { useRef, useImperativeHandle, forwardRef, useEffect } from "react";

interface VideoDisplayProps {
  videoUrl: string;
  isVisible: boolean;
  onReady?: () => void;
}

export interface VideoDisplayRef {
  navigateToTime: (seconds: number) => void;
}

export const VideoDisplay = forwardRef<VideoDisplayRef, VideoDisplayProps>(
  ({ videoUrl, isVisible, onReady }, ref) => {
    const iframeRef = useRef<HTMLIFrameElement>(null);

    // Debug ref initialization
    useEffect(() => {
      console.log(`VideoDisplay: Component mounted/updated. isVisible: ${isVisible}, videoUrl: ${videoUrl}`);
      if (iframeRef.current) {
        console.log(`VideoDisplay: iframe ref is available`);
        // Notify parent that we're ready
        if (onReady) {
          onReady();
        }
      } else {
        console.log(`VideoDisplay: iframe ref is not available yet`);
      }
    }, [isVisible, videoUrl, onReady]);

    const extractVideoId = (url: string): string | null => {
      const regex = /(?:youtube\.com\/watch\?v=|youtu\.be\/)([a-zA-Z0-9_-]{11})/;
      const match = url.match(regex);
      return match ? match[1] : null;
    };

    const navigateToTime = (seconds: number) => {
      try {
        // Validate seconds before navigation
        if (seconds < 0) {
          console.warn(`VideoDisplay: Cannot navigate to negative seconds: ${seconds}`);
          return;
        }
        
        // Reasonable upper limit (2 hours = 7200 seconds)
        if (seconds > 7200) {
          console.warn(`VideoDisplay: Cannot navigate beyond reasonable limit: ${seconds}s`);
          return;
        }
        
        if (iframeRef.current) {
          const videoId = extractVideoId(videoUrl);
          if (videoId) {
            // Update the iframe src with the new timestamp
            const newUrl = `https://www.youtube.com/embed/${videoId}?start=${seconds}&autoplay=1&rel=0&modestbranding=1`;
            iframeRef.current.src = newUrl;
            console.log(`VideoDisplay: Updated iframe src to navigate to ${seconds} seconds`);
          } else {
            console.warn(`VideoDisplay: Could not extract video ID from URL: ${videoUrl}`);
          }
        } else {
          console.warn(`VideoDisplay: iframe ref is not available`);
        }
      } catch (error) {
        console.error(`VideoDisplay: Error in navigateToTime:`, error);
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

    // Only render if visible and we have a valid video ID
    if (!isVisible || !videoId) {
      console.log(`VideoDisplay: Not rendering. isVisible: ${isVisible}, videoId: ${videoId}`);
      return null;
    }

    console.log(`VideoDisplay: Rendering with videoId: ${videoId}`);

    return (
      <div className="bg-white/[0.03] rounded-lg border border-white/[0.1] p-6 h-full flex flex-col">
        <div className="mb-4 flex-shrink-0">
          <h3 className="text-lg font-medium text-white mb-2">Video Player</h3>
          <p className="text-sm text-zinc-400">
            Watch the video and use timestamps to navigate
          </p>
        </div>

        <div className="relative w-full flex-1 min-h-0">
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

        <div className="mt-4 flex items-center justify-between text-sm text-zinc-400 flex-shrink-0">
          <span>Video ID: {videoId}</span>
          <span>Click timestamps to navigate</span>
        </div>
      </div>
    );
  }
);

VideoDisplay.displayName = "VideoDisplay"; 