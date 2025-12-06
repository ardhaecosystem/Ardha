"use client";

import { useState, useRef, useEffect } from "react";

interface PriorityOption {
  value: string;
  label: string;
  icon: string;
  color: string;
}

const priorityOptions: PriorityOption[] = [
  { value: "all", label: "All Priorities", icon: "◉", color: "text-white" },
  { value: "low", label: "Low", icon: "🔵", color: "text-blue-400" },
  { value: "medium", label: "Medium", icon: "🟡", color: "text-yellow-400" },
  { value: "high", label: "High", icon: "🔴", color: "text-red-400" },
  { value: "urgent", label: "Urgent", icon: "🚨", color: "text-red-500" },
];

interface PrioritySelectProps {
  value: string;
  onChange: (value: string) => void;
}

export function PrioritySelect({ value, onChange }: PrioritySelectProps) {
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const selectedOption =
    priorityOptions.find((opt) => opt.value === value) || priorityOptions[0];

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        containerRef.current &&
        !containerRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  return (
    <div ref={containerRef} className="relative">
      {/* Selected Value Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-4 h-10 rounded-lg glass-panel border border-white/10 text-white text-sm hover:border-neon-blue/50 transition-all duration-200 min-w-[160px]"
      >
        <span className="text-base">{selectedOption.icon}</span>
        <span className="flex-1 text-left">{selectedOption.label}</span>
        <svg
          className={`w-4 h-4 text-white/60 transition-transform duration-200 ${isOpen ? "rotate-180" : ""}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M19 9l-7 7-7-7"
          />
        </svg>
      </button>

      {/* Dropdown Menu */}
      {isOpen && (
        <div className="absolute top-full left-0 mt-2 w-full min-w-[200px] backdrop-blur-xl bg-black/80 border border-white/20 rounded-lg shadow-2xl z-50 overflow-hidden animate-in fade-in slide-in-from-top-2 duration-200">
          {priorityOptions.map((option) => (
            <button
              key={option.value}
              onClick={() => {
                onChange(option.value);
                setIsOpen(false);
              }}
              className={`w-full flex items-center gap-3 px-4 py-2.5 text-left text-sm transition-all duration-150 ${
                value === option.value
                  ? "bg-neon-blue/15 border-l-2 border-neon-blue"
                  : "hover:bg-white/5"
              }`}
            >
              <span className="text-lg">{option.icon}</span>
              <span className={option.color}>{option.label}</span>
              {value === option.value && (
                <svg
                  className="w-4 h-4 ml-auto text-neon-blue"
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
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
