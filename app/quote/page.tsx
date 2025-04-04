"use client"

import Link from "next/link"
import { ArrowLeft } from "lucide-react"
import NewQuoteForm from './NewQuoteForm2'

export default function QuotePage() {

  return (
    <div className="flex flex-col min-h-screen bg-[#0A1525]">
      <main className="flex-1 container py-10">
        <div className="flex items-center mb-8">
          <Link href="/" className="mr-2 text-white hover:text-[#5fe496] transition-colors">
            <ArrowLeft className="h-5 w-5" />
            <span className="sr-only">Back</span>
          </Link>
          <h1 className="text-3xl font-andale text-white">Get Instant Quote</h1>
        </div>

        <div className="max-w-7xl mx-auto">
          <div className="space-y-4 mb-8">
            <p className="text-lg text-white/70 font-avenir">
              Upload your design and get a real-time quote with DFM analysis. No sales calls, no middlemen, no markup.
            </p>
          </div>

          <NewQuoteForm />

          <div className="mt-12 glow-card rounded-none border border-[#1E2A45] bg-[#0C1F3D]/30 p-8 backdrop-blur-sm">
            <h2 className="text-2xl font-andale mb-4">How it Works</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              <div className="space-y-3">
                <div className="w-10 h-10 rounded-none bg-[#0A1525] border border-[#1E2A45] flex items-center justify-center">
                  <span className="font-andale text-[#5fe496] text-lg">1</span>
                </div>
                <h3 className="text-lg font-andale">Upload Your Model</h3>
                <p className="text-white/70 font-avenir">
                  Upload your 3D model file (STL or STEP) and select your manufacturing options.
                </p>
              </div>

              <div className="space-y-3">
                <div className="w-10 h-10 rounded-none bg-[#0A1525] border border-[#1E2A45] flex items-center justify-center">
                  <span className="font-andale text-[#5fe496] text-lg">2</span>
                </div>
                <h3 className="text-lg font-andale">DFM Analysis</h3>
                <p className="text-white/70 font-avenir">
                  Our system analyzes your design for manufacturability, identifying any issues that could affect production.
                </p>
              </div>

              <div className="space-y-3">
                <div className="w-10 h-10 rounded-none bg-[#0A1525] border border-[#1E2A45] flex items-center justify-center">
                  <span className="font-andale text-[#5fe496] text-lg">3</span>
                </div>
                <h3 className="text-lg font-andale">Get Your Quote</h3>
                <p className="text-white/70 font-avenir">
                  Receive an instant price quote and lead time estimate based on your specifications.
                </p>
              </div>

              <div className="space-y-3">
                <div className="w-10 h-10 rounded-none bg-[#0A1525] border border-[#1E2A45] flex items-center justify-center">
                  <span className="font-andale text-[#5fe496] text-lg">4</span>
                </div>
                <h3 className="text-lg font-andale">Place Order</h3>
                <p className="text-white/70 font-avenir">
                  When you're ready, place your order with a single click. We'll manufacture your parts and ship them directly to you.
                </p>
              </div>
            </div>
          </div>
        </div>
      </main>

      <footer className="w-full border-t border-[#1E2A45] py-6">
        <div className="container flex flex-col items-center justify-between gap-4 md:h-16 md:flex-row">
          <p className="text-center text-sm text-white/50 font-avenir md:text-left">
            © {new Date().getFullYear()} Proton Demand. All rights reserved.
          </p>
          <div className="flex gap-4">
            <Link href="/terms" className="text-sm text-white/50 hover:text-white font-avenir">
              Terms
            </Link>
            <Link href="/privacy" className="text-sm text-white/50 hover:text-white font-avenir">
              Privacy
            </Link>
            <Link href="/contact" className="text-sm text-white/50 hover:text-white font-avenir">
              Contact
            </Link>
          </div>
        </div>
      </footer>
    </div>
  )
}

