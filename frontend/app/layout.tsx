import type React from "react"
import type { Metadata } from "next"
import { Inter } from "next/font/google"
import "./globals.css"
import { Providers } from "@/lib/providers"

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
})

export const metadata: Metadata = {
  title: "Regulatory Assistant",
  description:
    "Evidence-led regulatory research: FDA, EMA, China agencies, trials, literature, and more.",
  // Icons from `app/favicon.ico`, `app/apple-icon.png` (Safari-friendly .ico + touch icon).
  // Omit `metadata.icons` so Next merges file conventions without dropping apple-touch.
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en" className={inter.variable}>
      <body className="font-sans antialiased">
        <Providers>
          {children}
        </Providers>
      </body>
    </html>
  )
}











