"use client";

import { useState, useRef, useEffect } from "react";
import {
  useChats,
  useChat,
  useChatMessages,
  useSendMessage,
  useCreateChat,
  type Chat,
} from "@/hooks/use-chats";
import { ChatSidebar } from "@/components/chat/sidebar";
import { ChatMessage, TypingIndicator } from "@/components/chat/message";

type ChatMode = "research" | "architect" | "implement" | "debug" | "chat";

export default function ChatPage() {
  const [selectedChatId, setSelectedChatId] = useState<string | null>(null);
  const [inputMessage, setInputMessage] = useState("");
  const [selectedModel, setSelectedModel] = useState(
    "anthropic/claude-sonnet-4-20250514",
  );

  const { data: chats = [] } = useChats();
  const { data: chat, isLoading: chatLoading } = useChat(selectedChatId);
  const { data: messages = [], isLoading: messagesLoading } =
    useChatMessages(selectedChatId);
  const sendMessage = useSendMessage();
  const createChat = useCreateChat();
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Get selected chat from list if detailed data not loaded yet
  const selectedChat = chat || chats.find((c: Chat) => c.id === selectedChatId);

  // Debug logging
  useEffect(() => {
    if (selectedChatId) {
      console.log("[ChatPage] Selected chat ID:", selectedChatId);
      console.log("[ChatPage] Has chat data:", !!selectedChat);
      console.log("[ChatPage] Chat loading:", chatLoading);
    }
  }, [selectedChatId, selectedChat, chatLoading]);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = async () => {
    if (!inputMessage.trim() || !selectedChatId) return;

    const messageContent = inputMessage;
    setInputMessage(""); // Clear input immediately for better UX

    try {
      console.log("[ChatPage] Sending message to chat:", selectedChatId);
      await sendMessage.mutateAsync({
        chatId: selectedChatId,
        content: messageContent,
        model: selectedModel,
      });
      console.log("[ChatPage] Message sent successfully");
    } catch (error) {
      console.error("[ChatPage] Failed to send message:", error);
      setInputMessage(messageContent); // Restore message on error
      alert(
        `Failed to send message: ${error instanceof Error ? error.message : "Unknown error"}`,
      );
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleNewChat = () => {
    setSelectedChatId(null);
  };

  const handleCreateChat = async (mode: ChatMode = "chat") => {
    try {
      console.log("[ChatPage] Creating chat with mode:", mode);
      const newChat = await createChat.mutateAsync({ mode });
      console.log("[ChatPage] Created chat:", newChat);
      setSelectedChatId(newChat.id);
    } catch (error) {
      console.error("[ChatPage] Failed to create chat:", error);
      alert(
        `Failed to create chat: ${error instanceof Error ? error.message : "Unknown error"}`,
      );
    }
  };

  return (
    <div className="h-screen flex overflow-hidden">
      {/* Sidebar */}
      <ChatSidebar
        selectedChatId={selectedChatId}
        onSelectChat={setSelectedChatId}
        onNewChat={handleNewChat}
      />

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col">
        {selectedChatId && selectedChat ? (
          <>
            {/* Chat Header - Compact */}
            <div className="glass-panel border-b border-white/10 p-3">
              <div className="max-w-4xl mx-auto flex items-center justify-between">
                <div>
                  <h1 className="text-lg font-bold text-white">
                    {selectedChat.title}
                  </h1>
                  <p className="text-white/60 text-xs">
                    {messages.length}{" "}
                    {messages.length === 1 ? "message" : "messages"}
                  </p>
                </div>

                {/* Model Selector - Compact */}
                <div className="flex items-center gap-2">
                  <select
                    value={selectedModel}
                    onChange={(e) => setSelectedModel(e.target.value)}
                    className="px-3 py-1.5 h-9 rounded-lg glass-panel border border-white/10 text-white text-xs focus:outline-none focus:ring-2 focus:ring-[hsl(var(--neon-blue))]/50 transition-all duration-200 cursor-pointer hover:border-white/20"
                  >
                    <option
                      value="anthropic/claude-sonnet-4-20250514"
                      className="bg-gray-900"
                    >
                      Claude Sonnet 4.5
                    </option>
                    <option
                      value="anthropic/claude-opus-4-20250514"
                      className="bg-gray-900"
                    >
                      Claude Opus 4.1
                    </option>
                    <option value="z-ai/glm-4.6" className="bg-gray-900">
                      GLM 4.6
                    </option>
                    <option
                      value="x-ai/grok-code-fast-1"
                      className="bg-gray-900"
                    >
                      Grok Code Fast
                    </option>
                    <option
                      value="google/gemini-2.0-flash-001:free"
                      className="bg-gray-900"
                    >
                      Gemini Flash
                    </option>
                  </select>

                  {/* Mode Badge - Compact */}
                  {selectedChat.mode !== "chat" && (
                    <div className="px-2.5 py-1 rounded-lg glass-panel border border-[hsl(var(--neon-purple))]/30 text-[hsl(var(--neon-purple))] text-xs font-medium capitalize">
                      {selectedChat.mode}
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Messages - Compact */}
            <div className="flex-1 overflow-y-auto p-4">
              <div className="max-w-4xl mx-auto space-y-4">
                {messagesLoading ? (
                  <div className="text-center py-12">
                    <div className="inline-block w-12 h-12 border-4 border-[hsl(var(--neon-blue))]/30 border-t-[hsl(var(--neon-blue))] rounded-full animate-spin" />
                    <p className="text-white/60 text-sm mt-4">
                      Loading messages...
                    </p>
                  </div>
                ) : messages.length > 0 ? (
                  <>
                    {messages.map((message) => (
                      <ChatMessage key={message.id} message={message} />
                    ))}
                    {sendMessage.isPending && <TypingIndicator />}
                  </>
                ) : (
                  <div className="text-center py-16">
                    <div className="text-6xl mb-4 animate-float-slow">💬</div>
                    <h2 className="text-xl font-bold text-white mb-2">
                      Start the conversation
                    </h2>
                    <p className="text-white/60 text-sm">
                      Send a message to begin chatting with AI
                    </p>
                  </div>
                )}
                <div ref={messagesEndRef} />
              </div>
            </div>

            {/* Input Area - Compact */}
            <div className="glass-panel border-t border-white/10 p-3">
              <div className="max-w-4xl mx-auto">
                <div className="flex gap-2">
                  <textarea
                    value={inputMessage}
                    onChange={(e) => setInputMessage(e.target.value)}
                    onKeyDown={handleKeyPress}
                    placeholder="Type your message... (Shift+Enter for new line)"
                    rows={2}
                    disabled={sendMessage.isPending}
                    className="flex-1 px-3 py-2 rounded-lg glass-panel border border-white/10 text-white text-sm placeholder-white/40 focus:outline-none focus:ring-2 focus:ring-[hsl(var(--neon-blue))]/50 transition-all duration-200 resize-none disabled:opacity-50 disabled:cursor-not-allowed"
                  />
                  <button
                    onClick={handleSend}
                    disabled={!inputMessage.trim() || sendMessage.isPending}
                    className="px-4 h-auto rounded-lg bg-gradient-to-r from-purple-600 to-pink-600 text-white font-semibold hover:shadow-lg hover:shadow-purple-500/50 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
                    aria-label="Send message"
                  >
                    {sendMessage.isPending ? (
                      <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    ) : (
                      <svg
                        className="w-4 h-4"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"
                        />
                      </svg>
                    )}
                  </button>
                </div>
                <div className="mt-1.5 text-white/40 text-xs flex items-center justify-between">
                  <span>Press Enter to send, Shift+Enter for new line</span>
                  {inputMessage.length > 0 && (
                    <span className="text-[hsl(var(--neon-blue))]">
                      {inputMessage.length} characters
                    </span>
                  )}
                </div>
              </div>
            </div>
          </>
        ) : (
          // No chat selected - Welcome State
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center max-w-2xl px-6">
              <div className="text-6xl mb-4 animate-float-slow">✨</div>
              <h2 className="text-2xl font-bold text-white mb-3">
                Welcome to Ardha AI Chat
              </h2>
              <p className="text-white/60 mb-6 text-sm">
                Select a chat from the sidebar or create a new one to start
                conversing with AI
              </p>

              {/* Mode Selection Cards - Enhanced Glass */}
              <div className="grid grid-cols-2 gap-4 max-w-2xl mx-auto">
                <button
                  onClick={() => handleCreateChat("chat")}
                  disabled={createChat.isPending}
                  className="group relative p-6 rounded-xl backdrop-blur-xl bg-white/5 border border-white/10 hover:border-neon-blue/50 hover:bg-white/10 transition-all duration-300 text-left disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {/* Glow Effect */}
                  <div className="absolute inset-0 rounded-xl bg-gradient-to-br from-blue-500 to-cyan-500 opacity-0 group-hover:opacity-20 blur-xl transition-opacity duration-300" />

                  {/* Content */}
                  <div className="relative">
                    <div className="text-4xl mb-3 group-hover:scale-110 transition-transform duration-300">
                      💬
                    </div>
                    <h3 className="text-lg font-bold text-white mb-1.5 group-hover:text-glow transition-all duration-300">
                      General Chat
                    </h3>
                    <p className="text-white/60 text-sm">
                      Start a conversation
                    </p>
                  </div>

                  {/* Arrow Icon */}
                  <div className="absolute bottom-6 right-6 opacity-0 group-hover:opacity-100 transition-opacity duration-300">
                    <svg
                      className="w-5 h-5 text-neon-blue"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M13 7l5 5m0 0l-5 5m5-5H6"
                      />
                    </svg>
                  </div>
                </button>

                <button
                  onClick={() => handleCreateChat("research")}
                  disabled={createChat.isPending}
                  className="group relative p-6 rounded-xl backdrop-blur-xl bg-white/5 border border-white/10 hover:border-purple-500/50 hover:bg-white/10 transition-all duration-300 text-left disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {/* Glow Effect */}
                  <div className="absolute inset-0 rounded-xl bg-gradient-to-br from-purple-500 to-pink-500 opacity-0 group-hover:opacity-20 blur-xl transition-opacity duration-300" />

                  {/* Content */}
                  <div className="relative">
                    <div className="text-4xl mb-3 group-hover:scale-110 transition-transform duration-300">
                      🔬
                    </div>
                    <h3 className="text-lg font-bold text-white mb-1.5 group-hover:text-glow transition-all duration-300">
                      Research Mode
                    </h3>
                    <p className="text-white/60 text-sm">Analyze and explore</p>
                  </div>

                  {/* Arrow Icon */}
                  <div className="absolute bottom-6 right-6 opacity-0 group-hover:opacity-100 transition-opacity duration-300">
                    <svg
                      className="w-5 h-5 text-neon-blue"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M13 7l5 5m0 0l-5 5m5-5H6"
                      />
                    </svg>
                  </div>
                </button>

                <button
                  onClick={() => handleCreateChat("architect")}
                  disabled={createChat.isPending}
                  className="group relative p-6 rounded-xl backdrop-blur-xl bg-white/5 border border-white/10 hover:border-pink-500/50 hover:bg-white/10 transition-all duration-300 text-left disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {/* Glow Effect */}
                  <div className="absolute inset-0 rounded-xl bg-gradient-to-br from-pink-500 to-rose-500 opacity-0 group-hover:opacity-20 blur-xl transition-opacity duration-300" />

                  {/* Content */}
                  <div className="relative">
                    <div className="text-4xl mb-3 group-hover:scale-110 transition-transform duration-300">
                      🏗️
                    </div>
                    <h3 className="text-lg font-bold text-white mb-1.5 group-hover:text-glow transition-all duration-300">
                      Architect Mode
                    </h3>
                    <p className="text-white/60 text-sm">Design systems</p>
                  </div>

                  {/* Arrow Icon */}
                  <div className="absolute bottom-6 right-6 opacity-0 group-hover:opacity-100 transition-opacity duration-300">
                    <svg
                      className="w-5 h-5 text-neon-blue"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M13 7l5 5m0 0l-5 5m5-5H6"
                      />
                    </svg>
                  </div>
                </button>

                <button
                  onClick={() => handleCreateChat("implement")}
                  disabled={createChat.isPending}
                  className="group relative p-6 rounded-xl backdrop-blur-xl bg-white/5 border border-white/10 hover:border-green-500/50 hover:bg-white/10 transition-all duration-300 text-left disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {/* Glow Effect */}
                  <div className="absolute inset-0 rounded-xl bg-gradient-to-br from-green-500 to-emerald-500 opacity-0 group-hover:opacity-20 blur-xl transition-opacity duration-300" />

                  {/* Content */}
                  <div className="relative">
                    <div className="text-4xl mb-3 group-hover:scale-110 transition-transform duration-300">
                      ⚡
                    </div>
                    <h3 className="text-lg font-bold text-white mb-1.5 group-hover:text-glow transition-all duration-300">
                      Implement Mode
                    </h3>
                    <p className="text-white/60 text-sm">Write code</p>
                  </div>

                  {/* Arrow Icon */}
                  <div className="absolute bottom-6 right-6 opacity-0 group-hover:opacity-100 transition-opacity duration-300">
                    <svg
                      className="w-5 h-5 text-neon-blue"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M13 7l5 5m0 0l-5 5m5-5H6"
                      />
                    </svg>
                  </div>
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
