/**
 * Client for /api/chat/* (httpOnly visitor cookie; use credentials: "include").
 * Set NEXT_PUBLIC_CHAT_RELATIVE=true and Next rewrites to proxy /api → backend if you need same-origin cookies in dev.
 */

import { slimQueryProcessingForPersist } from "./query-processing-snapshot"

function chatPath(path: string): string {
  const p = path.startsWith("/") ? path : `/${path}`
  if (!p.startsWith("/api/chat")) {
    return `/api/chat${p}`
  }
  return p
}

export function useRelativeChatApi(): boolean {
  return process.env.NEXT_PUBLIC_CHAT_RELATIVE === "true"
}

export function chatApiUrl(path: string): string {
  const full = chatPath(path)
  if (typeof window !== "undefined" && useRelativeChatApi()) {
    return full
  }
  const base = (process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8001").replace(/\/$/, "")
  return `${base}${full}`
}

export async function chatFetch(path: string, init?: RequestInit): Promise<Response> {
  const url = chatApiUrl(path)
  const headers = new Headers(init?.headers)
  if (init?.body && typeof init.body === "string" && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json")
  }
  return fetch(url, { ...init, credentials: "include", headers })
}

export async function chatBootstrap(): Promise<{ visitor_id: string; created: boolean }> {
  const res = await chatFetch("/visitors/bootstrap", { method: "POST" })
  if (!res.ok) {
    const t = await res.text()
    throw new Error(t || `bootstrap ${res.status}`)
  }
  return res.json() as Promise<{ visitor_id: string; created: boolean }>
}

export type RemoteSessionMeta = {
  id: string
  title: string
  updatedAt: number
  starred?: boolean
  titlePinned?: boolean
  variant?: string
}

function normalizeSession(j: Record<string, unknown>): RemoteSessionMeta {
  const updated = j.updated_at ?? j.updatedAt
  const t =
    typeof updated === "string"
      ? Date.parse(updated)
      : typeof updated === "number"
        ? updated
        : Date.now()
  return {
    id: String(j.id),
    title: String(j.title ?? "New chat"),
    updatedAt: Number.isFinite(t) ? t : Date.now(),
    starred: Boolean(j.starred),
    titlePinned: Boolean(j.title_pinned ?? j.titlePinned),
    variant: typeof j.variant === "string" ? j.variant : undefined,
  }
}

export async function chatListSessions(variant?: string): Promise<RemoteSessionMeta[]> {
  const q = variant ? `?variant=${encodeURIComponent(variant)}` : ""
  const res = await chatFetch(`/sessions${q}`, { method: "GET" })
  if (!res.ok) {
    const t = await res.text()
    throw new Error(t || `sessions ${res.status}`)
  }
  const raw = await res.json()
  const arr = Array.isArray(raw) ? raw : []
  return (arr as Record<string, unknown>[]).map(normalizeSession)
}

export async function chatCreateSession(body: {
  id?: string
  title?: string
  variant?: string
}): Promise<RemoteSessionMeta> {
  const res = await chatFetch("/sessions", {
    method: "POST",
    body: JSON.stringify({
      title: body.title ?? "New chat",
      variant: body.variant ?? "regulatory",
      ...(body.id ? { id: body.id } : {}),
    }),
  })
  if (!res.ok) {
    const t = await res.text()
    throw new Error(t || `create session ${res.status}`)
  }
  const j = (await res.json()) as Record<string, unknown>
  return normalizeSession(j)
}

export async function chatPatchSession(
  id: string,
  body: { title?: string; starred?: boolean; titlePinned?: boolean },
): Promise<RemoteSessionMeta> {
  const payload: Record<string, unknown> = {}
  if (body.title !== undefined) payload.title = body.title
  if (body.starred !== undefined) payload.starred = body.starred
  if (body.titlePinned !== undefined) payload.title_pinned = body.titlePinned
  const res = await chatFetch(`/sessions/${id}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  })
  if (!res.ok) {
    const t = await res.text()
    throw new Error(t || `patch session ${res.status}`)
  }
  const j = (await res.json()) as Record<string, unknown>
  return normalizeSession(j)
}

export async function chatDeleteSession(id: string): Promise<void> {
  const res = await chatFetch(`/sessions/${id}`, { method: "DELETE" })
  if (!res.ok) {
    const t = await res.text()
    throw new Error(t || `delete session ${res.status}`)
  }
}

export type RemoteMessageDTO = {
  id: string
  role: string
  content: string
  timestamp: string
  metadata?: Record<string, unknown>
}

export async function chatListMessages(sessionId: string): Promise<RemoteMessageDTO[]> {
  const res = await chatFetch(`/sessions/${sessionId}/messages`, { method: "GET" })
  if (!res.ok) {
    const t = await res.text()
    throw new Error(t || `messages ${res.status}`)
  }
  const j = (await res.json()) as { messages?: Record<string, unknown>[] }
  const rows = j.messages ?? []
  return rows.map((m) => ({
    id: String(m.id),
    role: String(m.role),
    content: String(m.content),
    timestamp: String(m.created_at ?? m.timestamp ?? new Date().toISOString()),
    metadata: (m.metadata as Record<string, unknown>) || undefined,
  }))
}

/** JSON-safe, size-bounded metadata for Postgres chat persistence (avoids 413 / serialization failures). */
export function slimMetadataForChatPersist(meta: Record<string, unknown> | undefined): Record<string, unknown> {
  if (!meta || typeof meta !== "object") return {}
  const out: Record<string, unknown> = {}
  const ct = meta.citations
  if (Array.isArray(ct)) {
    out.citations = ct.slice(0, 80).map((c) => {
      if (c && typeof c === "object" && "text" in (c as object)) {
        const o = c as Record<string, unknown>
        return {
          text: String(o.text ?? "").slice(0, 4000),
          url: typeof o.url === "string" ? o.url.slice(0, 2000) : "",
        }
      }
      return { text: String(c).slice(0, 4000), url: "" }
    })
  }
  if (typeof meta.confidence === "number" || typeof meta.confidence === "string") {
    out.confidence = meta.confidence
  }
  if (typeof meta.data_quality === "string") out.data_quality = meta.data_quality
  if (typeof meta.processing_time === "number" && Number.isFinite(meta.processing_time)) {
    out.processing_time = meta.processing_time
  }
  const agents = meta.agents_used
  if (Array.isArray(agents)) {
    out.agents_used = agents.filter((x): x is string => typeof x === "string").slice(0, 100)
  }
  const qp = slimQueryProcessingForPersist(meta.query_processing)
  if (qp) out.query_processing = qp
  return out
}

export async function chatAppendMessage(
  sessionId: string,
  body: { id: string; role: string; content: string; metadata?: Record<string, unknown> },
): Promise<void> {
  const res = await chatFetch(`/sessions/${sessionId}/messages`, {
    method: "POST",
    body: JSON.stringify({
      content: body.content,
      metadata: body.metadata ?? {},
      client_message_id: body.id,
    }),
  })
  if (!res.ok) {
    const t = await res.text()
    throw new Error(t || `append message ${res.status}`)
  }
}

export async function chatCompleteTurn(
  sessionId: string,
  body: {
    user_message_client_id: string
    assistant: { id: string; content: string; metadata?: Record<string, unknown> }
  },
): Promise<void> {
  const idem = `asst-${body.user_message_client_id}-${body.assistant.id}`
  const res = await chatFetch(`/sessions/${sessionId}/complete-turn`, {
    method: "POST",
    body: JSON.stringify({
      content: body.assistant.content,
      metadata: slimMetadataForChatPersist(body.assistant.metadata),
      idempotency_key: idem,
    }),
    headers: { "Idempotency-Key": idem },
  })
  if (!res.ok) {
    const t = await res.text()
    throw new Error(t || `complete-turn ${res.status}`)
  }
}

export function remoteChatPersistenceEnabled(): boolean {
  return process.env.NEXT_PUBLIC_CHAT_PERSISTENCE === "true"
}
