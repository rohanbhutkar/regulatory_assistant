import { NextResponse } from "next/server"
import type { NextRequest } from "next/server"

const REGULATORY = "/regulatory-intelligence"

/** Files served from `public/` live at the URL root; allow them through so middleware does not redirect to REGULATORY. */
const PUBLIC_FILE_EXT = /\.(ico|png|jpe?g|gif|webp|svg|avif|woff2?|ttf|eot|txt|webmanifest)$/i

function isPublicPath(pathname: string): boolean {
  if (pathname === REGULATORY || pathname.startsWith(`${REGULATORY}/`)) return true
  if (pathname.startsWith("/_next")) return true
  if (pathname === "/icon" || pathname.startsWith("/icon/")) return true
  if (pathname === "/apple-icon" || pathname.startsWith("/apple-icon/")) return true
  if (pathname === "/favicon.ico") return true
  if (PUBLIC_FILE_EXT.test(pathname)) return true
  return false
}

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl
  if (isPublicPath(pathname)) {
    return NextResponse.next()
  }
  const url = request.nextUrl.clone()
  url.pathname = REGULATORY
  return NextResponse.redirect(url)
}

export const config = {
  matcher: ["/((?!_next/static|_next/image).*)"],
}
