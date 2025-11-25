// API Response Types
// These match the backend Pydantic schemas

export interface User {
  id: string;
  email: string;
  username: string;
  full_name: string;
  is_active: boolean;
  is_superuser: boolean;
  created_at: string;
  updated_at: string;
}

export interface Project {
  id: string;
  name: string;
  description: string | null;
  owner_id: string;
  created_at: string;
  updated_at: string;
}

export interface Task {
  id: string;
  title: string;
  description: string | null;
  status: "TODO" | "IN_PROGRESS" | "IN_REVIEW" | "DONE" | "CANCELLED";
  priority: "LOW" | "MEDIUM" | "HIGH" | "URGENT";
  project_id: string;
  assigned_to_id: string | null;
  created_by_id: string;
  due_date: string | null;
  created_at: string;
  updated_at: string;
}

export interface Chat {
  id: string;
  title: string;
  mode: "research" | "architect" | "implement" | "debug" | "chat";
  project_id: string | null;
  user_id: string;
  created_at: string;
  updated_at: string;
}

// Add more types as needed
