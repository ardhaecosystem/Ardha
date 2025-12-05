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
            {/* Chat Header */}
            <div className="glass-panel border-b border-white/10 p-4">
              <div className="max-w-4xl mx-auto flex items-center justify-between">
                <div>
                  <h1 className="text-xl font-bold text-white text-glow">
                    {selectedChat.title}
                  </h1>
                  <p className="text-white/60 text-sm">
                    {messages.length}{" "}
                    {messages.length === 1 ? "message" : "messages"}
                  </p>
                </div>

                {/* Model Selector */}
                <div className="flex items-center gap-3">
                  <select
                    value={selectedModel}
                    onChange={(e) => setSelectedModel(e.target.value)}
                    className="px-4 py-2 rounded-lg glass-panel border border-white/10 text-white text-sm focus:outline-none focus:ring-2 focus:ring-[hsl(var(--neon-blue))]/50 transition-all duration-200 cursor-pointer hover:border-white/20"
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

                  {/* Mode Badge */}
                  {selectedChat.mode !== "chat" && (
                    <div className="px-3 py-1.5 rounded-lg glass-panel border border-[hsl(var(--neon-purple))]/30 text-[hsl(var(--neon-purple))] text-sm font-medium capitalize">
                      {selectedChat.mode}
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-6">
              <div className="max-w-4xl mx-auto space-y-6">
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
                  <div className="text-center py-20">
                    <div className="text-7xl mb-6 animate-float-slow">💬</div>
                    <h2 className="text-2xl font-bold text-white mb-2 text-glow">
                      Start the conversation
                    </h2>
                    <p className="text-white/60">
                      Send a message to begin chatting with AI
                    </p>
                  </div>
                )}
                <div ref={messagesEndRef} />
              </div>
            </div>

            {/* Input Area */}
            <div className="glass-panel border-t border-white/10 p-4">
              <div className="max-w-4xl mx-auto">
                <div className="flex gap-3">
                  <textarea
                    value={inputMessage}
                    onChange={(e) => setInputMessage(e.target.value)}
                    onKeyDown={handleKeyPress}
                    placeholder="Type your message... (Shift+Enter for new line)"
                    rows={3}
                    disabled={sendMessage.isPending}
                    className="flex-1 px-4 py-3 rounded-xl glass-panel border border-white/10 text-white placeholder-white/40 focus:outline-none focus:ring-2 focus:ring-[hsl(var(--neon-blue))]/50 transition-all duration-200 resize-none disabled:opacity-50 disabled:cursor-not-allowed"
                  />
                  <button
                    onClick={handleSend}
                    disabled={!inputMessage.trim() || sendMessage.isPending}
                    className="px-6 py-3 rounded-xl bg-gradient-to-r from-[hsl(var(--neon-purple))] to-[hsl(var(--neon-pink))] text-white font-semibold hover:shadow-lg hover:shadow-purple-500/50 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
                    aria-label="Send message"
                  >
                    {sendMessage.isPending ? (
                      <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    ) : (
                      <svg
                        className="w-5 h-5"
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
                <div className="mt-2 text-white/40 text-xs flex items-center justify-between">
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
            <div className="text-center max-w-2xl px-8">
              <div className="text-8xl mb-6 animate-float-slow">✨</div>
              <h2 className="text-4xl font-bold text-white mb-4 text-glow">
                Welcome to Ardha AI Chat
              </h2>
              <p className="text-white/60 mb-8 text-lg">
                Select a chat from the sidebar or create a new one to start
                conversing with AI
              </p>

              {/* Quick Actions */}
              <div className="grid grid-cols-2 gap-4 max-w-md mx-auto">
                <button
                  onClick={() => handleCreateChat("chat")}
                  disabled={createChat.isPending}
                  className="p-6 rounded-xl glass-panel border border-white/10 hover:border-[hsl(var(--neon-blue))]/50 transition-all duration-300 group disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <div className="text-3xl mb-2">💬</div>
                  <div className="text-white font-medium">General Chat</div>
                  <div className="text-white/40 text-xs mt-1">
                    Start a conversation
                  </div>
                </button>

                <button
                  onClick={() => handleCreateChat("research")}
                  disabled={createChat.isPending}
                  className="p-6 rounded-xl glass-panel border border-white/10 hover:border-[hsl(var(--neon-purple))]/50 transition-all duration-300 group disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <div className="text-3xl mb-2">🔬</div>
                  <div className="text-white font-medium">Research Mode</div>
                  <div className="text-white/40 text-xs mt-1">
                    Analyze and explore
                  </div>
                </button>

                <button
                  onClick={() => handleCreateChat("architect")}
                  disabled={createChat.isPending}
                  className="p-6 rounded-xl glass-panel border border-white/10 hover:border-[hsl(var(--neon-pink))]/50 transition-all duration-300 group disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <div className="text-3xl mb-2">🏗️</div>
                  <div className="text-white font-medium">Architect Mode</div>
                  <div className="text-white/40 text-xs mt-1">
                    Design systems
                  </div>
                </button>

                <button
                  onClick={() => handleCreateChat("implement")}
                  disabled={createChat.isPending}
                  className="p-6 rounded-xl glass-panel border border-white/10 hover:border-green-500/50 transition-all duration-300 group disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <div className="text-3xl mb-2">⚡</div>
                  <div className="text-white font-medium">Implement Mode</div>
                  <div className="text-white/40 text-xs mt-1">Write code</div>
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
