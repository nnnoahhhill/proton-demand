"use client"

import Link from "next/link"
import Image from "next/image"
import { useState } from "react"
import { Button } from "@/components/ui/button"
import { GlowButton } from "@/components/ui/glow-button"
import { X, Menu } from "lucide-react"
import { CartIcon } from "@/components/CartIcon"

export function Navigation() {
  const [isOpen, setIsOpen] = useState(false)

  return (
    <header className="border-b border-[#1E2A45] bg-[#0A1525] sticky top-0 z-50">
      <div className="container px-4 md:px-6 py-4">
        <div className="flex items-center justify-between">
          <Link href="/" className="flex items-center">
            <Image
              src="/brand_assets/PD_dark_horizontal.svg"
              alt="proton|demand logo"
              width={180}
              height={40}
              className="h-8 w-auto"
            />
          </Link>
          <nav className="hidden md:flex items-center space-x-8">
            <Link href="/services" className="text-sm font-andale hover:text-[#F46036] transition-colors">
              Services
            </Link>
            <Link href="/about-us" className="text-sm font-andale hover:text-[#F46036] transition-colors">
              About Us
            </Link>
            <div className="flex items-center space-x-6">
              <CartIcon />
              <GlowButton asChild>
                <Link href="/quote">Get Instant Quote</Link>
              </GlowButton>
            </div>
          </nav>
          <div className="md:hidden flex items-center space-x-4">
            <CartIcon />
            <Button variant="ghost" size="icon" onClick={() => setIsOpen(!isOpen)}>
              {isOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
              <span className="sr-only">Toggle menu</span>
            </Button>
          </div>
        </div>
      </div>
      {isOpen && (
        <div className="md:hidden border-t border-[#1E2A45]">
          <div className="container px-4 py-4 flex flex-col space-y-4">
            <Link
              href="/services"
              className="text-sm font-andale hover:text-[#F46036] transition-colors"
              onClick={() => setIsOpen(false)}
            >
              Services
            </Link>
            <Link
              href="/about-us"
              className="text-sm font-andale hover:text-[#F46036] transition-colors"
              onClick={() => setIsOpen(false)}
            >
              About Us
            </Link>
            <Link
              href="/checkout"
              className="text-sm font-andale hover:text-[#F46036] transition-colors"
              onClick={() => setIsOpen(false)}
            >
              Cart
            </Link>
            <GlowButton asChild className="w-full" onClick={() => setIsOpen(false)}>
              <Link href="/quote">Get Instant Quote</Link>
            </GlowButton>
          </div>
        </div>
      )}
    </header>
  )
}

