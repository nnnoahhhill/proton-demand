import type React from "react"
import "@/app/globals.css"
import { Kode_Mono as Andale_Mono } from "next/font/google"
import { ThemeProvider } from "@/components/theme-provider"
import { Navigation } from "@/components/navigation"
import { Footer } from "@/components/footer"
import { AnimatedBackground } from "@/components/animated-background"
import { CartProvider } from "@/lib/cart"
import { LoadingProvider } from "@/lib/loading-context"

const andaleMono = Andale_Mono({
  weight: "400",
  subsets: ["latin"],
})

export const metadata = {
  title: "proton|demand - Pay less. Build more.",
  description:
    "Industrial-grade manufacturing at founder-friendly prices. Upload your 3D models and get instant quotes.",
    generator: 'v0.dev'
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${andaleMono.className} dark bg-[#0A1525] text-white antialiased`}>
        <ThemeProvider attribute="class" defaultTheme="dark" enableSystem={false} forcedTheme="dark">
          <CartProvider>
            <LoadingProvider>
              <AnimatedBackground />
              <div className="flex min-h-screen flex-col relative z-10">
                <Navigation />
                <main className="flex-1">{children}</main>
                <Footer />
              </div>
            </LoadingProvider>
          </CartProvider>
        </ThemeProvider>
      </body>
    </html>
  )
}



import './globals.css'