export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface HealthResponse {
  status: "ok" | "degraded";
  database: "connected" | "unreachable";
  timestamp: string;
}

export async function fetchHealth(): Promise<HealthResponse> {
  const response = await fetch(`${API_BASE_URL}/health`, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`Backend responded with ${response.status}`);
  }
  return response.json();
}

export interface User {
  id: string;
  email: string;
  created_at: string;
}

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function parseErrorDetail(response: Response): Promise<string> {
  try {
    const body = await response.json();
    return body.detail ?? `Request failed with ${response.status}`;
  } catch {
    return `Request failed with ${response.status}`;
  }
}

export async function signup(email: string, password: string): Promise<User> {
  const response = await fetch(`${API_BASE_URL}/auth/signup`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ email, password }),
  });
  if (!response.ok) throw new ApiError(response.status, await parseErrorDetail(response));
  return response.json();
}

export async function login(email: string, password: string): Promise<User> {
  const response = await fetch(`${API_BASE_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ email, password }),
  });
  if (!response.ok) throw new ApiError(response.status, await parseErrorDetail(response));
  return response.json();
}

export async function logout(): Promise<void> {
  await fetch(`${API_BASE_URL}/auth/logout`, {
    method: "POST",
    credentials: "include",
  });
}

export async function fetchCurrentUser(): Promise<User | null> {
  const response = await fetch(`${API_BASE_URL}/auth/me`, {
    credentials: "include",
    cache: "no-store",
  });
  if (response.status === 401) return null;
  if (!response.ok) throw new ApiError(response.status, await parseErrorDetail(response));
  return response.json();
}

export interface Organization {
  id: string;
  name: string;
  slug: string;
  created_at: string;
  role: "owner" | "admin" | "manager" | "member" | "viewer";
}

export async function listOrganizations(): Promise<Organization[]> {
  const response = await fetch(`${API_BASE_URL}/organizations`, { credentials: "include", cache: "no-store" });
  if (!response.ok) throw new ApiError(response.status, await parseErrorDetail(response));
  return response.json();
}

export async function createOrganization(name: string): Promise<Organization> {
  const response = await fetch(`${API_BASE_URL}/organizations`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ name }),
  });
  if (!response.ok) throw new ApiError(response.status, await parseErrorDetail(response));
  return response.json();
}

export interface DocumentItem {
  id: string;
  filename: string;
  content_type: string;
  size_bytes: number;
  status: "pending" | "processing" | "ready" | "failed";
  page_count: number | null;
  error_message: string | null;
  created_at: string;
}

export async function listDocuments(orgId: string): Promise<DocumentItem[]> {
  const response = await fetch(`${API_BASE_URL}/organizations/${orgId}/documents`, {
    credentials: "include",
    cache: "no-store",
  });
  if (!response.ok) throw new ApiError(response.status, await parseErrorDetail(response));
  return response.json();
}

export async function uploadDocument(orgId: string, file: File): Promise<DocumentItem> {
  const formData = new FormData();
  formData.append("file", file);
  const response = await fetch(`${API_BASE_URL}/organizations/${orgId}/documents`, {
    method: "POST",
    credentials: "include",
    body: formData,
  });
  if (!response.ok) throw new ApiError(response.status, await parseErrorDetail(response));
  return response.json();
}

export async function deleteDocument(orgId: string, documentId: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/organizations/${orgId}/documents/${documentId}`, {
    method: "DELETE",
    credentials: "include",
  });
  if (!response.ok) throw new ApiError(response.status, await parseErrorDetail(response));
}

export type OrganizationRole = "owner" | "admin" | "manager" | "member" | "viewer";

export interface Member {
  user_id: string;
  email: string;
  role: OrganizationRole;
  created_at: string;
}

export async function listMembers(orgId: string): Promise<Member[]> {
  const response = await fetch(`${API_BASE_URL}/organizations/${orgId}/members`, {
    credentials: "include",
    cache: "no-store",
  });
  if (!response.ok) throw new ApiError(response.status, await parseErrorDetail(response));
  return response.json();
}

export async function addMember(orgId: string, email: string, role: OrganizationRole): Promise<Member> {
  const response = await fetch(`${API_BASE_URL}/organizations/${orgId}/members`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ email, role }),
  });
  if (!response.ok) throw new ApiError(response.status, await parseErrorDetail(response));
  return response.json();
}

export async function updateMemberRole(orgId: string, userId: string, role: OrganizationRole): Promise<Member> {
  const response = await fetch(`${API_BASE_URL}/organizations/${orgId}/members/${userId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ role }),
  });
  if (!response.ok) throw new ApiError(response.status, await parseErrorDetail(response));
  return response.json();
}

export async function removeMember(orgId: string, userId: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/organizations/${orgId}/members/${userId}`, {
    method: "DELETE",
    credentials: "include",
  });
  if (!response.ok) throw new ApiError(response.status, await parseErrorDetail(response));
}

export interface Citation {
  chunk_id: string;
  document_id: string;
  filename: string;
  page_number: number | null;
  snippet: string;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations: Citation[] | null;
  created_at: string;
}

export interface ChatResponse {
  conversation_id: string;
  message: ChatMessage;
}

export async function sendChatMessage(
  orgId: string,
  message: string,
  conversationId: string | null
): Promise<ChatResponse> {
  const response = await fetch(`${API_BASE_URL}/organizations/${orgId}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ message, conversation_id: conversationId }),
  });
  if (!response.ok) throw new ApiError(response.status, await parseErrorDetail(response));
  return response.json();
}

export interface ConversationSummary {
  id: string;
  title: string;
  created_at: string;
}

export async function listConversations(orgId: string): Promise<ConversationSummary[]> {
  const response = await fetch(`${API_BASE_URL}/organizations/${orgId}/conversations`, {
    credentials: "include",
    cache: "no-store",
  });
  if (!response.ok) throw new ApiError(response.status, await parseErrorDetail(response));
  return response.json();
}

export async function getConversationMessages(orgId: string, conversationId: string): Promise<ChatMessage[]> {
  const response = await fetch(`${API_BASE_URL}/organizations/${orgId}/conversations/${conversationId}/messages`, {
    credentials: "include",
    cache: "no-store",
  });
  if (!response.ok) throw new ApiError(response.status, await parseErrorDetail(response));
  return response.json();
}
