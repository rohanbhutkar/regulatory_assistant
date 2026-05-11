/** Index of regulatory chat sessions (metadata only). Message payloads live per-session keys. */

export const REGULATORY_SESSIONS_INDEX_KEY = "regulatory-intelligence-sessions-index"

/** Same-tab updates (storage event only fires across tabs). */
export const REGULATORY_SESSIONS_CHANGED_EVENT = "regulatory-intelligence-sessions-changed"

function notifyRegulatorySessionsChanged(): void {
  if (typeof window === "undefined") return
  window.dispatchEvent(new CustomEvent(REGULATORY_SESSIONS_CHANGED_EVENT))
}

/** Subscribe for `useSyncExternalStore` (same-tab + cross-tab). */
export function subscribeRegulatorySessionIndex(onStoreChange: () => void): () => void {
  if (typeof window === "undefined") return () => {}
  const onStorage = (e: StorageEvent) => {
    if (e.key === REGULATORY_SESSIONS_INDEX_KEY || e.key === null) onStoreChange()
  }
  const onCustom = () => onStoreChange()
  window.addEventListener("storage", onStorage)
  window.addEventListener(REGULATORY_SESSIONS_CHANGED_EVENT, onCustom)
  return () => {
    window.removeEventListener("storage", onStorage)
    window.removeEventListener(REGULATORY_SESSIONS_CHANGED_EVENT, onCustom)
  }
}

/** Server / SSR snapshot (empty); client will re-sync without hydration mismatch. */
export function getRegulatorySessionIndexServerSnapshot(): string {
  return "[]"
}

/**
 * Client snapshot for useSyncExternalStore. Ensures at least one session exists (writes default to localStorage).
 */
export function getRegulatorySessionIndexSnapshot(): string {
  if (typeof window === "undefined") return "[]"
  let list = loadSessionIndex()
  if (list.length === 0) {
    const id = crypto.randomUUID()
    list = [{ id, title: "New chat", updatedAt: Date.now() }]
    saveSessionIndex(list)
  }
  return JSON.stringify(list)
}

export type RegulatorySessionMeta = {
  id: string
  title: string
  updatedAt: number
  starred?: boolean
  /** Set when the user renames from the sidebar; auto-title from messages won't overwrite */
  titlePinned?: boolean
}

export function chatStorageKey(sessionId: string): string {
  return `regulatory-intelligence-chat-${sessionId}`
}

export function loadSessionIndex(): RegulatorySessionMeta[] {
  if (typeof window === "undefined") return []
  try {
    const raw = localStorage.getItem(REGULATORY_SESSIONS_INDEX_KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw) as RegulatorySessionMeta[]
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

export function saveSessionIndex(sessions: RegulatorySessionMeta[]): void {
  if (typeof window === "undefined") return
  try {
    const next = JSON.stringify(sessions)
    const prev = localStorage.getItem(REGULATORY_SESSIONS_INDEX_KEY)
    if (prev === next) return
    localStorage.setItem(REGULATORY_SESSIONS_INDEX_KEY, next)
    notifyRegulatorySessionsChanged()
  } catch {
    /* ignore */
  }
}

export function removeChatPayload(sessionId: string): void {
  if (typeof window === "undefined") return
  try {
    localStorage.removeItem(chatStorageKey(sessionId))
  } catch {
    /* ignore */
  }
}

/** Derive a short sidebar title from the first user message. */
export function titleFromFirstUserMessage(content: string): string {
  const stripped = content
    .replace(/\*\*/g, "")
    .replace(/#{1,6}\s*/g, "")
    .replace(/`{1,3}[^`]*`{1,3}/g, "")
    .replace(/\n+/g, " ")
    .trim()
  if (!stripped) return "New chat"
  const t = stripped.length > 56 ? `${stripped.slice(0, 53)}…` : stripped
  return t
}

/** Remove all regulatory-intelligence-* keys (index + per-chat payloads). */
export function clearAllRegulatoryChatData(): void {
  if (typeof window === "undefined") return
  try {
    const keys = Object.keys(localStorage).filter((k) => k.startsWith("regulatory-intelligence-"))
    for (const k of keys) {
      localStorage.removeItem(k)
    }
    notifyRegulatorySessionsChanged()
  } catch {
    /* ignore */
  }
}
