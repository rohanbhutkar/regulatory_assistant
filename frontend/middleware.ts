import { NextResponse } from "next/server"
import type { NextRequest } from "next/server"

const HOME = "/"

/** Files served from `public/` live at the URL root; allow them through so middleware does not redirect to HOME. */
const PUBLIC_FILE_EXT = /\.(ico|png|jpe?g|gif|webp|svg|avif|woff2?|ttf|eot|txt|webmanifest)$/i

/** First path segment for known app routes (cold loads must not be forced to HOME). */
const APP_FIRST_SEGMENTS = new Set([
  "research",
  "study-designer",
  "cpp-admin",
  "usdm-export",
  "commercial",
  "asset-management",
  "test-context",
  "fmv-analysis",
  "asset-strategy",
  "clinical-operations",
])

function isAllowedPath(pathname: string): boolean {
  if (pathname === HOME) return true
  if (pathname.startsWith("/_next")) return true
  if (pathname === "/icon" || pathname.startsWith("/icon/")) return true
  if (pathname === "/apple-icon" || pathname.startsWith("/apple-icon/")) return true
  if (pathname === "/favicon.ico") return true
  if (PUBLIC_FILE_EXT.test(pathname)) return true

  const first = pathname.split("/").filter(Boolean)[0]
  if (!first) return false
  return APP_FIRST_SEGMENTS.has(first)
}

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl
  if (pathname === "/regulatory-intelligence" || pathname.startsWith("/regulatory-intelligence/")) {
    const url = request.nextUrl.clone()
    url.pathname = "/"
    return NextResponse.redirect(url, 308)
  }
  if (isAllowedPath(pathname)) {
    return NextResponse.next()
  }
  const url = request.nextUrl.clone()
  url.pathname = HOME
  return NextResponse.redirect(url)
}

export const config = {
  matcher: ["/((?!_next/static|_next/image).*)"],
}
