import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useAuthStore } from "@/lib/auth-store";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface Message {
  id: string;
  role: "user" | "assistant" | "system" | "tool";
  content: string;
  created_at: string;
  ai_model?: string; // Backend returns 'ai_model', not 'model_used'
  tokens_input?: number;
  tokens_output?: number;
  cost?: number;
  message_metadata?: Record<string, any>;
}

export interface Chat {
  id: string;
  title: string;
  mode: "research" | "architect" | "implement" | "debug" | "chat";
  created_at: string;
  updated_at: string;
  is_archived: boolean;
  project_id?: string;
  total_tokens: number;
  total_cost: number;
}

// Get all user chats
export function useChats() {
  const { accessToken } = useAuthStore();

  return useQuery({
    queryKey: ["chats"],
    queryFn: async () => {
      console.log("[useChats] Fetching chats...");
      const response = await fetch(`${API_BASE_URL}/api/v1/chats`, {
        headers: {
          Authorization: `Bearer ${accessToken}`,
        },
      });

      if (!response.ok) {
        const error = await response.text();
        console.error("[useChats] Error:", response.status, error);
        throw new Error(`Failed to fetch chats: ${response.status}`);
      }

      const data = (await response.json()) as Chat[];
      console.log("[useChats] Fetched chats:", data.length);
      return data;
    },
    enabled: !!accessToken,
  });
}

// Get single chat details
export function useChat(chatId: string | null) {
  const { accessToken } = useAuthStore();

  return useQuery({
    queryKey: ["chat", chatId],
    queryFn: async () => {
      if (!chatId) return null;

      console.log("[useChat] Fetching chat:", chatId);
      const response = await fetch(`${API_BASE_URL}/api/v1/chats/${chatId}`, {
        headers: {
          Authorization: `Bearer ${accessToken}`,
        },
      });

      if (!response.ok) {
        const error = await response.text();
        console.error("[useChat] Error:", response.status, error);
        throw new Error(`Failed to fetch chat: ${response.status}`);
      }

      const data = await response.json();
      console.log("[useChat] Fetched chat summary:", data);
      // Backend returns ChatSummaryResponse: { chat, message_stats, recent_messages }
      // Extract just the chat object
      return data.chat as Chat;
    },
    enabled: !!accessToken && !!chatId,
    staleTime: 0, // Always fetch fresh data
    gcTime: 0, // Don't keep in cache when not in use
  });
}

// Get chat messages (history)
export function useChatMessages(chatId: string | null) {
  const { accessToken } = useAuthStore();

  return useQuery({
    queryKey: ["chat-messages", chatId],
    queryFn: async () => {
      if (!chatId) return [];

      console.log("[useChatMessages] Fetching messages for chat:", chatId);
      const response = await fetch(
        `${API_BASE_URL}/api/v1/chats/${chatId}/history`,
        {
          headers: {
            Authorization: `Bearer ${accessToken}`,
          },
        },
      );

      if (!response.ok) {
        const error = await response.text();
        console.error("[useChatMessages] Error:", response.status, error);
        throw new Error(`Failed to fetch messages: ${response.status}`);
      }

      const data = (await response.json()) as Message[];
      console.log("[useChatMessages] Fetched messages:", data.length);
      return data;
    },
    enabled: !!accessToken && !!chatId,
    refetchInterval: 5000, // Auto-refresh every 5 seconds
  });
}

// Create new chat
export function useCreateChat() {
  const { accessToken } = useAuthStore();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: {
      mode?: "research" | "architect" | "implement" | "debug" | "chat";
      project_id?: string;
    }) => {
      console.log("[useCreateChat] Creating chat with:", data);
      const response = await fetch(`${API_BASE_URL}/api/v1/chats`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${accessToken}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          mode: data.mode || "chat",
          project_id: data.project_id || null,
        }),
      });

      if (!response.ok) {
        const error = await response.json();
        console.error("[useCreateChat] Error:", response.status, error);
        throw new Error(error.detail || "Failed to create chat");
      }

      const chat = (await response.json()) as Chat;
      console.log("[useCreateChat] Created chat:", chat);
      return chat;
    },
    onSuccess: (newChat) => {
      // Optimistically add new chat to the chats list
      queryClient.setQueryData(["chats"], (oldChats: Chat[] = []) => {
        // Check if chat already exists (shouldn't, but be safe)
        if (oldChats.some((c) => c.id === newChat.id)) {
          return oldChats;
        }
        // Add new chat at the beginning
        return [newChat, ...oldChats];
      });

      // Cache the chat data immediately so it's available when selected
      queryClient.setQueryData(["chat", newChat.id], newChat);

      // Set empty messages array for new chat
      queryClient.setQueryData(["chat-messages", newChat.id], []);

      console.log(
        "[useCreateChat] Optimistically added chat to cache:",
        newChat.id,
      );
    },
  });
}

// Send message to chat (returns streaming response - waits for completion then refetches)
export function useSendMessage() {
  const { accessToken } = useAuthStore();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      chatId,
      content,
      model,
    }: {
      chatId: string;
      content: string;
      model?: string;
    }) => {
      console.log(
        "[useSendMessage] Sending message to chat:",
        chatId,
        "Model:",
        model,
      );

      const response = await fetch(
        `${API_BASE_URL}/api/v1/chats/${chatId}/messages`,
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${accessToken}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            content,
            model: model || "anthropic/claude-sonnet-4-20250514",
          }),
        },
      );

      if (!response.ok) {
        const error = await response
          .json()
          .catch(() => ({ detail: "Failed to send message" }));
        console.error("[useSendMessage] Error:", response.status, error);
        throw new Error(error.detail || "Failed to send message");
      }

      // Backend returns Server-Sent Events stream
      // Read the entire stream until completion
      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error("No response body");
      }

      const decoder = new TextDecoder();
      let buffer = "";

      try {
        while (true) {
          const { done, value } = await reader.read();

          if (done) {
            console.log("[useSendMessage] Stream completed");
            break;
          }

          buffer += decoder.decode(value, { stream: true });

          // Process complete SSE messages (ending with \n\n)
          const messages = buffer.split("\n\n");
          buffer = messages.pop() || ""; // Keep incomplete message in buffer

          for (const message of messages) {
            if (message.startsWith("data: ")) {
              const data = message.slice(6); // Remove 'data: ' prefix
              if (data === "[DONE]") {
                console.log("[useSendMessage] Received [DONE] signal");
                break;
              }
              // Log the chunks being received
              console.log(
                "[useSendMessage] Received chunk:",
                data.substring(0, 50) + "...",
              );
            }
          }
        }
      } finally {
        reader.releaseLock();
      }

      console.log("[useSendMessage] Message sent and response received");
      return { success: true };
    },
    onSuccess: (_, variables) => {
      console.log("[useSendMessage] Invalidating queries to refetch messages");
      // Invalidate all related queries to refetch the new messages
      queryClient.invalidateQueries({ queryKey: ["chat", variables.chatId] });
      queryClient.invalidateQueries({
        queryKey: ["chat-messages", variables.chatId],
      });
      queryClient.invalidateQueries({ queryKey: ["chats"] });
    },
  });
}

// Archive chat
export function useArchiveChat() {
  const { accessToken } = useAuthStore();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (chatId: string) => {
      console.log("[useArchiveChat] Archiving chat:", chatId);
      const response = await fetch(
        `${API_BASE_URL}/api/v1/chats/${chatId}/archive`,
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${accessToken}`,
          },
        },
      );

      if (!response.ok) {
        const error = await response
          .json()
          .catch(() => ({ detail: "Failed to archive chat" }));
        console.error("[useArchiveChat] Error:", response.status, error);
        throw new Error(error.detail || "Failed to archive chat");
      }

      const chat = (await response.json()) as Chat;
      console.log("[useArchiveChat] Archived chat:", chat);
      return chat;
    },
    onSuccess: (_, chatId) => {
      queryClient.invalidateQueries({ queryKey: ["chat", chatId] });
      queryClient.invalidateQueries({ queryKey: ["chats"] });
    },
  });
}

// Delete chat (hard delete)
export function useDeleteChat() {
  const { accessToken } = useAuthStore();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (chatId: string) => {
      console.log("[useDeleteChat] Deleting chat:", chatId);
      const response = await fetch(`${API_BASE_URL}/api/v1/chats/${chatId}`, {
        method: "DELETE",
        headers: {
          Authorization: `Bearer ${accessToken}`,
        },
      });

      if (!response.ok) {
        const error = await response
          .json()
          .catch(() => ({ detail: "Failed to delete chat" }));
        console.error("[useDeleteChat] Error:", response.status, error);
        throw new Error(error.detail || "Failed to delete chat");
      }

      console.log("[useDeleteChat] Deleted chat successfully");
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["chats"] });
    },
  });
}
