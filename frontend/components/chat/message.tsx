"use client";

import { Message } from "@/hooks/use-chats";
import { useState } from "react";

interface MessageProps {
  message: Message;
}

export function ChatMessage({ message }: MessageProps) {
  const [copied, setCopied] = useState(false);
  const isUser = message.role === "user";

  // Don't render system messages
  if (message.role === "system") {
    return null;
  }

  const handleCopy = () => {
    navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // Calculate total tokens
  const totalTokens =
    (message.tokens_input || 0) + (message.tokens_output || 0);

  return (
    <div
      className={`flex gap-3 ${isUser ? "flex-row-reverse" : "flex-row"} group animate-in fade-in slide-in-from-bottom-2 duration-300`}
    >
      {/* Avatar - More compact */}
      <div
        className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
          isUser
            ? "bg-gradient-to-br from-purple-500 to-pink-500"
            : "glass-panel border border-[hsl(var(--neon-blue))]/50"
        }`}
      >
        {isUser ? (
          <span className="text-white font-semibold text-xs">U</span>
        ) : (
          <svg
            className="w-4 h-4 text-[hsl(var(--neon-blue))]"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
            />
          </svg>
        )}
      </div>

      {/* Message Content - More compact */}
      <div
        className={`flex-1 max-w-3xl ${isUser ? "text-right" : "text-left"}`}
      >
        <div
          className={`inline-block px-4 py-2.5 rounded-xl glass-panel relative group/message transition-all duration-300 ${
            isUser
              ? "bg-gradient-to-br from-purple-500/20 to-pink-500/20 border-purple-500/30 hover:border-purple-500/50"
              : "border-[hsl(var(--neon-blue))]/30 hover:border-[hsl(var(--neon-blue))]/50"
          }`}
        >
          {/* Copy Button - Smaller */}
          <button
            onClick={handleCopy}
            className="absolute top-2 right-2 opacity-0 group-hover/message:opacity-100 transition-opacity duration-200 p-1.5 rounded-lg hover:bg-white/10 z-10"
            aria-label="Copy message"
          >
            {copied ? (
              <svg
                className="w-3.5 h-3.5 text-green-400"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M5 13l4 4L19 7"
                />
              </svg>
            ) : (
              <svg
                className="w-3.5 h-3.5 text-white/60 hover:text-white"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"
                />
              </svg>
            )}
          </button>

          {/* Message Text - Smaller font */}
          <div className="text-white/90 text-sm leading-relaxed whitespace-pre-wrap pr-8">
            {message.content}
          </div>

          {/* Metadata - Smaller */}
          <div className="flex items-center gap-2 mt-1.5 text-white/40 text-xs">
            <span>
              {new Date(message.created_at).toLocaleTimeString([], {
                hour: "2-digit",
                minute: "2-digit",
              })}
            </span>
            {message.ai_model && (
              <>
                <span>•</span>
                <span className="text-[hsl(var(--neon-blue))]">
                  {message.ai_model.split("/")[1] || message.ai_model}
                </span>
              </>
            )}
            {totalTokens > 0 && (
              <>
                <span>•</span>
                <span>{totalTokens.toLocaleString()} tokens</span>
              </>
            )}
            {message.cost && (
              <>
                <span>•</span>
                <span className="text-green-400">
                  ${message.cost.toFixed(4)}
                </span>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// Typing indicator component
export function TypingIndicator() {
  return (
    <div className="flex gap-4">
      <div className="flex-shrink-0 w-10 h-10 rounded-full glass-panel border-2 border-[hsl(var(--neon-blue))]/50 flex items-center justify-center">
        <div className="w-2 h-2 rounded-full bg-[hsl(var(--neon-blue))] animate-pulse" />
      </div>
      <div className="glass-panel p-4 rounded-2xl border-[hsl(var(--neon-blue))]/30">
        <div className="flex gap-2">
          <div
            className="w-2 h-2 rounded-full bg-[hsl(var(--neon-blue))] animate-bounce"
            style={{ animationDelay: "0ms" }}
          />
          <div
            className="w-2 h-2 rounded-full bg-[hsl(var(--neon-blue))] animate-bounce"
            style={{ animationDelay: "150ms" }}
          />
          <div
            className="w-2 h-2 rounded-full bg-[hsl(var(--neon-blue))] animate-bounce"
            style={{ animationDelay: "300ms" }}
          />
        </div>
      </div>
    </div>
  );
}
