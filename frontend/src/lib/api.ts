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

export interface ComparisonResult {
  document_a: string;
  document_b: string;
  summary: string;
  similarities: string[];
  differences: string[];
  contradictions: string[];
  truncated: boolean;
}

export async function compareDocuments(
  orgId: string,
  documentIdA: string,
  documentIdB: string
): Promise<ComparisonResult> {
  const response = await fetch(`${API_BASE_URL}/organizations/${orgId}/documents/compare`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ document_id_a: documentIdA, document_id_b: documentIdB }),
  });
  if (!response.ok) throw new ApiError(response.status, await parseErrorDetail(response));
  return response.json();
}

export interface ExtractedField {
  label: string;
  value: string;
}

export interface ExtractionResult {
  document: string;
  fields: ExtractedField[];
  truncated: boolean;
}

export async function extractDocument(orgId: string, documentId: string): Promise<ExtractionResult> {
  const response = await fetch(`${API_BASE_URL}/organizations/${orgId}/documents/${documentId}/extract`, {
    method: "POST",
    credentials: "include",
  });
  if (!response.ok) throw new ApiError(response.status, await parseErrorDetail(response));
  return response.json();
}

export interface ReportResult {
  title: string;
  documents: string[];
  overview: string;
  key_findings: string[];
  risks_or_gaps: string[];
  recommendations: string[];
  truncated: boolean;
}

export async function generateReport(orgId: string, documentIds: string[], focus?: string): Promise<ReportResult> {
  const response = await fetch(`${API_BASE_URL}/organizations/${orgId}/documents/report`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ document_ids: documentIds, focus: focus || null }),
  });
  if (!response.ok) throw new ApiError(response.status, await parseErrorDetail(response));
  return response.json();
}

export interface ResearchCitation {
  chunk_id: string;
  document_id: string;
  filename: string;
  page_number: number | null;
  snippet: string;
}

export interface ResearchFinding {
  claim: string;
  confidence: "verified" | "single_source";
  citations: ResearchCitation[];
}

export interface ResearchReport {
  topic: string;
  summary: string;
  findings: ResearchFinding[];
  gaps: string[];
  documents_used: string[];
}

export async function runResearch(orgId: string, topic: string): Promise<ResearchReport> {
  const response = await fetch(`${API_BASE_URL}/organizations/${orgId}/research`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ topic }),
  });
  if (!response.ok) throw new ApiError(response.status, await parseErrorDetail(response));
  return response.json();
}

export type ConnectorProvider = "google" | "slack";

export interface Connector {
  id: string;
  provider: ConnectorProvider;
  account_label: string;
  created_at: string;
}

export async function listConnectors(orgId: string): Promise<Connector[]> {
  const response = await fetch(`${API_BASE_URL}/organizations/${orgId}/connectors`, {
    credentials: "include",
    cache: "no-store",
  });
  if (!response.ok) throw new ApiError(response.status, await parseErrorDetail(response));
  return response.json();
}

async function getAuthorizeUrl(orgId: string, provider: ConnectorProvider): Promise<string> {
  const response = await fetch(`${API_BASE_URL}/organizations/${orgId}/connectors/${provider}/authorize`, {
    credentials: "include",
  });
  if (!response.ok) throw new ApiError(response.status, await parseErrorDetail(response));
  const data = await response.json();
  return data.authorize_url;
}

export const getGoogleAuthorizeUrl = (orgId: string) => getAuthorizeUrl(orgId, "google");
export const getSlackAuthorizeUrl = (orgId: string) => getAuthorizeUrl(orgId, "slack");

export async function deleteConnector(orgId: string, connectorId: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/organizations/${orgId}/connectors/${connectorId}`, {
    method: "DELETE",
    credentials: "include",
  });
  if (!response.ok) throw new ApiError(response.status, await parseErrorDetail(response));
}

export interface EmailMessage {
  id: string;
  subject: string;
  sender: string;
  date: string;
  snippet: string;
}

export async function listConnectorEmails(orgId: string, connectorId: string): Promise<EmailMessage[]> {
  const response = await fetch(`${API_BASE_URL}/organizations/${orgId}/connectors/${connectorId}/emails`, {
    credentials: "include",
    cache: "no-store",
  });
  if (!response.ok) throw new ApiError(response.status, await parseErrorDetail(response));
  return response.json();
}

export interface SlackChannel {
  id: string;
  name: string;
  is_member: boolean;
  num_members: number | null;
}

export async function listConnectorChannels(orgId: string, connectorId: string): Promise<SlackChannel[]> {
  const response = await fetch(`${API_BASE_URL}/organizations/${orgId}/connectors/${connectorId}/channels`, {
    credentials: "include",
    cache: "no-store",
  });
  if (!response.ok) throw new ApiError(response.status, await parseErrorDetail(response));
  return response.json();
}

export interface DraftEmailSummary {
  draft_text: string;
  source_email_count: number;
}

export async function draftEmailSummary(
  orgId: string,
  gmailConnectorId: string,
  maxResults = 10
): Promise<DraftEmailSummary> {
  const response = await fetch(`${API_BASE_URL}/organizations/${orgId}/agent/draft-email-summary`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ gmail_connector_id: gmailConnectorId, max_results: maxResults }),
  });
  if (!response.ok) throw new ApiError(response.status, await parseErrorDetail(response));
  return response.json();
}

export interface PostToSlackResult {
  posted: boolean;
  channel_id: string;
  slack_ts: string;
}

export async function postToSlack(
  orgId: string,
  slackConnectorId: string,
  channelId: string,
  message: string
): Promise<PostToSlackResult> {
  const response = await fetch(`${API_BASE_URL}/organizations/${orgId}/agent/post-to-slack`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ slack_connector_id: slackConnectorId, channel_id: channelId, message }),
  });
  if (!response.ok) throw new ApiError(response.status, await parseErrorDetail(response));
  return response.json();
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

export interface EvalCase {
  question: string;
  expected_keywords: string[];
}

export interface EvalCaseResult {
  question: string;
  answer: string;
  retrieved_chunk_count: number;
  retrieval_hit: boolean | null;
  faithfulness: number | null;
  relevance: number | null;
  judge_notes: string | null;
}

export interface EvalReport {
  results: EvalCaseResult[];
  retrieval_hit_rate: number | null;
  average_faithfulness: number | null;
  average_relevance: number | null;
}

export async function runEvaluation(orgId: string, cases: EvalCase[]): Promise<EvalReport> {
  const response = await fetch(`${API_BASE_URL}/organizations/${orgId}/evaluation/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ cases }),
  });
  if (!response.ok) throw new ApiError(response.status, await parseErrorDetail(response));
  return response.json();
}

export type SubscriptionStatus = "on_trial" | "active" | "paused" | "past_due" | "unpaid" | "cancelled" | "expired";

export interface Subscription {
  status: SubscriptionStatus;
  variant_name: string;
  renews_at: string | null;
  ends_at: string | null;
}

export async function getSubscription(orgId: string): Promise<Subscription | null> {
  const response = await fetch(`${API_BASE_URL}/organizations/${orgId}/billing/subscription`, {
    credentials: "include",
    cache: "no-store",
  });
  if (!response.ok) throw new ApiError(response.status, await parseErrorDetail(response));
  return response.json();
}

export async function createCheckout(orgId: string): Promise<string> {
  const response = await fetch(`${API_BASE_URL}/organizations/${orgId}/billing/checkout`, {
    method: "POST",
    credentials: "include",
  });
  if (!response.ok) throw new ApiError(response.status, await parseErrorDetail(response));
  const data = await response.json();
  return data.checkout_url;
}

export interface Usage {
  is_paid_plan: boolean;
  document_count: number;
  document_limit: number | null;
  message_count: number;
  message_limit: number | null;
}

export async function getUsage(orgId: string): Promise<Usage> {
  const response = await fetch(`${API_BASE_URL}/organizations/${orgId}/billing/usage`, {
    credentials: "include",
    cache: "no-store",
  });
  if (!response.ok) throw new ApiError(response.status, await parseErrorDetail(response));
  return response.json();
}
