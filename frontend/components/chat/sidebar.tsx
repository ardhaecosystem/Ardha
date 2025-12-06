"use client";

import {
  useChats,
  useCreateChat,
  useDeleteChat,
  type Chat,
} from "@/hooks/use-chats";
import { useState } from "react";

interface ChatSidebarProps {
  selectedChatId: string | null;
  onSelectChat: (chatId: string) => void;
  onNewChat: () => void;
}

export function ChatSidebar({
  selectedChatId,
  onSelectChat,
  onNewChat,
}: ChatSidebarProps) {
  const { data: chats = [], isLoading } = useChats();
  const createChat = useCreateChat();
  const deleteChat = useDeleteChat();
  const [searchQuery, setSearchQuery] = useState("");
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const filteredChats = chats.filter((chat) =>
    chat.title.toLowerCase().includes(searchQuery.toLowerCase()),
  );

  const handleNewChat = async () => {
    try {
      console.log("[ChatSidebar] Creating new chat...");
      const newChat = await createChat.mutateAsync({
        mode: "chat",
      });
      console.log("[ChatSidebar] Created chat:", newChat);
      onSelectChat(newChat.id);
    } catch (error) {
      console.error("[ChatSidebar] Failed to create chat:", error);
      alert(
        `Failed to create chat: ${error instanceof Error ? error.message : "Unknown error"}`,
      );
    }
  };

  const handleDeleteChat = async (chatId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (
      !confirm(
        "Are you sure you want to delete this chat? This cannot be undone.",
      )
    )
      return;

    setDeletingId(chatId);
    try {
      console.log("[ChatSidebar] Deleting chat:", chatId);
      await deleteChat.mutateAsync(chatId);
      if (selectedChatId === chatId) {
        onNewChat();
      }
      console.log("[ChatSidebar] Chat deleted successfully");
    } catch (error) {
      console.error("[ChatSidebar] Failed to delete chat:", error);
      alert(
        `Failed to delete chat: ${error instanceof Error ? error.message : "Unknown error"}`,
      );
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <div className="w-80 h-full glass-panel border-r border-white/10 flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-white/10">
        <button
          onClick={handleNewChat}
          disabled={createChat.isPending}
          className="w-full px-4 py-3 rounded-xl bg-gradient-to-r from-[hsl(var(--neon-purple))] to-[hsl(var(--neon-pink))] text-white font-semibold hover:shadow-lg hover:shadow-purple-500/50 transition-all duration-200 flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {createChat.isPending ? (
            <>
              <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              <span>Creating...</span>
            </>
          ) : (
            <>
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
                  d="M12 4v16m8-8H4"
                />
              </svg>
              <span>New Chat</span>
            </>
          )}
        </button>
      </div>

      {/* Search */}
      <div className="p-4">
        <div className="relative">
          <input
            type="text"
            placeholder="Search chats..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full px-4 py-2 pl-10 rounded-lg glass-panel border border-white/10 text-white placeholder-white/40 focus:outline-none focus:ring-2 focus:ring-[hsl(var(--neon-blue))]/50 transition-all duration-200"
          />
          <svg
            className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-white/40"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
            />
          </svg>
        </div>
      </div>

      {/* Chat List */}
      <div className="flex-1 overflow-y-auto">
        {isLoading ? (
          <div className="p-4 space-y-3">
            {[1, 2, 3, 4, 5].map((i) => (
              <div
                key={i}
                className="h-16 rounded-lg glass-panel animate-pulse"
              />
            ))}
          </div>
        ) : filteredChats.length === 0 ? (
          <div className="p-8 text-center">
            <div className="text-4xl mb-4">💬</div>
            <p className="text-white/60 text-sm">
              {searchQuery ? "No chats found" : "No chats yet"}
            </p>
            <p className="text-white/40 text-xs mt-2">
              Click "New Chat" to start
            </p>
          </div>
        ) : (
          <div className="p-2 space-y-2">
            {filteredChats.map((chat) => (
              <button
                key={chat.id}
                onClick={() => onSelectChat(chat.id)}
                className={`group w-full p-3 rounded-lg text-left transition-all duration-200 ${
                  selectedChatId === chat.id
                    ? "backdrop-blur-xl bg-neon-blue/15 border border-neon-blue/50"
                    : "hover:backdrop-blur-xl hover:bg-white/5 border border-transparent"
                }`}
              >
                <div className="flex items-center justify-between mb-1">
                  <div className="text-white font-medium text-sm line-clamp-1 flex-1">
                    {chat.title}
                  </div>
                  {/* Delete button - show on hover */}
                  <button
                    onClick={(e) => handleDeleteChat(chat.id, e)}
                    disabled={deletingId === chat.id}
                    className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-red-500/20 transition-all duration-200"
                  >
                    {deletingId === chat.id ? (
                      <div className="w-3.5 h-3.5 border-2 border-red-400/30 border-t-red-400 rounded-full animate-spin" />
                    ) : (
                      <svg
                        className="w-3.5 h-3.5 text-red-400"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                        />
                      </svg>
                    )}
                  </button>
                </div>
                <div className="flex items-center gap-2">
                  <div className="text-white/40 text-xs">
                    {new Date(chat.updated_at).toLocaleDateString()}
                  </div>
                  {chat.mode && chat.mode !== "chat" && (
                    <span className="px-1.5 py-0.5 rounded text-xs bg-purple-500/20 text-purple-300 border border-purple-500/30">
                      {chat.mode}
                    </span>
                  )}
                </div>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Footer Stats */}
      <div className="p-4 border-t border-white/10">
        <div className="text-white/40 text-xs text-center">
          {chats.length} {chats.length === 1 ? "conversation" : "conversations"}
        </div>
      </div>
    </div>
  );
}
