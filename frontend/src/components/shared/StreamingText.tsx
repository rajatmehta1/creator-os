"use client";

import { useEffect, useState, useRef } from "react";
import { cn } from "@/lib/utils";

interface StreamingTextProps {
  text: string;
  isStreaming: boolean;
  speed?: number;
  className?: string;
}

export default function StreamingText({
  text,
  isStreaming,
  speed = 20,
  className,
}: StreamingTextProps) {
  const [displayedLength, setDisplayedLength] = useState(0);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const prevTextRef = useRef(text);

  useEffect(() => {
    // If text changed and we are streaming, continue from current position
    // If not streaming, show full text immediately
    if (!isStreaming) {
      setDisplayedLength(text.length);
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
      return;
    }

    // If the text has been replaced (not appended), reset
    if (!text.startsWith(prevTextRef.current.slice(0, displayedLength))) {
      setDisplayedLength(0);
    }
    prevTextRef.current = text;

    // Stream characters
    if (displayedLength < text.length) {
      intervalRef.current = setInterval(() => {
        setDisplayedLength((prev) => {
          if (prev >= text.length) {
            if (intervalRef.current) clearInterval(intervalRef.current);
            return prev;
          }
          return prev + 1;
        });
      }, speed);
    }

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [text, isStreaming, speed, displayedLength]);

  // Reset when text changes completely
  useEffect(() => {
    if (text !== prevTextRef.current && !text.startsWith(prevTextRef.current)) {
      setDisplayedLength(0);
    }
    prevTextRef.current = text;
  }, [text]);

  const visibleText = text.slice(0, displayedLength);
  const showCursor = isStreaming && displayedLength < text.length;

  return (
    <span className={cn("whitespace-pre-wrap", className)}>
      {visibleText}
      {showCursor && (
        <span className="ml-0.5 inline-block h-4 w-0.5 animate-pulse bg-primary" />
      )}
    </span>
  );
}
