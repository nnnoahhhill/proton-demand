import Link from "next/link"
import { GlowButton } from "@/components/ui/glow-button"
import { ModelCarousel } from "@/components/model-carousel"

export default function Home() {
  return (
    <div className="flex flex-col">
      {/* Hero Section */}
      <section className="relative py-20 md:py-32 border-b border-[#1E2A45] bg-[#0A1525] overflow-hidden">
        {/* Glow effect background */}
        <div className="absolute inset-0 z-0">
          <div className="absolute inset-0 bg-gradient-to-br from-[#0A1525] via-[#0C1F3D] to-[#0A1525] opacity-80"></div>
          <div className="absolute inset-0 bg-[#0A1525] opacity-90"></div>
          <div className="absolute inset-0 bg-gradient-to-r from-[#5fe496]/10 via-transparent to-[#F46036]/10"></div>
        </div>

        <div className="container px-4 md:px-6 relative z-10">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-12 items-center">
            <div className="space-y-6">
              <div className="inline-flex items-center rounded-none border border-[#1E2A45] bg-[#0A1525]/80 px-3 py-1 text-sm backdrop-blur-sm">
                <span className="text-[#5fe496] font-andale">BY FOUNDERS, FOR FOUNDERS</span>
              </div>
              <h1 className="text-4xl md:text-5xl lg:text-6xl font-andale tracking-tight leading-tight md:leading-tight lg:leading-tight">
                On-Demand Manufacturing <span className="text-[#F46036]">Without The Markup</span>
              </h1>
              <p className="text-xl text-white/70 font-avenir">Instant quotes that actually make sense</p>
              <div className="flex flex-col sm:flex-row gap-4">
                <GlowButton
                  asChild
                  size="lg"
                  className="bg-[#5fe496] text-[#0A1525] hover:bg-[#F46036] hover:text-white transition-all duration-300 font-bold text-base px-8 py-3"
                >
                  <Link href="/quote">Get Instant Quote</Link>
                </GlowButton>
              </div>
            </div>
            <div className="relative h-[500px] w-full">
              <ModelCarousel />
            </div>
          </div>
        </div>
      </section>

      {/* Why Section - Redesigned */}
      <section className="py-20 border-b border-[#1E2A45] bg-[#0A1525]">
        <div className="container px-4 md:px-6">
          <div className="max-w-5xl mx-auto">
            <div className="max-w-3xl mx-auto mb-16 flex flex-col items-center">
              <div className="inline-flex items-center rounded-none border border-[#1E2A45] bg-[#0A1525]/80 px-3 py-1 text-sm mb-4">
                <span className="text-[#5fe496] font-andale">WHY</span>
              </div>
              <h2 className="text-3xl font-andale tracking-tight mb-4 text-center">Why we're doing this</h2>
              <p className="text-lg text-white/70 font-avenir text-center">
                We're founders who got tired of overpaying for manufacturing. Now we're fixing it.
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
              <div className="glow-card rounded-none border border-[#1E2A45] bg-[#0C1F3D]/30 p-8 backdrop-blur-sm transition-all duration-300 hover:bg-[#0C1F3D]/50 text-center">
                <h3 className="text-xl font-andale mb-3">30-50% Lower Prices</h3>
                <p className="text-white/70 font-avenir">No sales teams, no middlemen, no markup.</p>
              </div>

              <div className="glow-card rounded-none border border-[#1E2A45] bg-[#0C1F3D]/30 p-8 backdrop-blur-sm transition-all duration-300 hover:bg-[#0C1F3D]/50 text-center">
                <h3 className="text-xl font-andale mb-3">Industry-Standard Quality</h3>
                <p className="text-white/70 font-avenir">Same machines, same materials, same quality standards.</p>
              </div>

              <div className="glow-card rounded-none border border-[#1E2A45] bg-[#0C1F3D]/30 p-8 backdrop-blur-sm transition-all duration-300 hover:bg-[#0C1F3D]/50 text-center">
                <h3 className="text-xl font-andale mb-3">Fast Turnaround</h3>
                <p className="text-white/70 font-avenir">Get parts in days, not weeks or months.</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* How It Works Section - Redesigned */}
      <section className="py-20 border-b border-[#1E2A45] bg-[#0A1525]">
        <div className="container px-4 md:px-6">
          <div className="max-w-5xl mx-auto">
            <div className="max-w-3xl mx-auto mb-16 flex flex-col items-center">
              <div className="inline-flex items-center rounded-none border border-[#1E2A45] bg-[#0A1525]/80 px-3 py-1 text-sm mb-4">
                <span className="text-[#F46036] font-andale">PROCESS</span>
              </div>
              <h2 className="text-3xl font-andale tracking-tight mb-4 text-center">How It Works</h2>
              <p className="text-lg text-white/70 font-avenir text-center">
                Get your parts manufactured in three simple steps.
              </p>
            </div>

            <div className="relative">
              {/* Connecting line */}
              <div className="hidden md:block absolute top-1/2 left-0 right-0 h-0.5 bg-gradient-to-r from-[#5fe496]/20 via-[#F46036]/20 to-[#5fe496]/20 transform -translate-y-1/2 z-0"></div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-12">
                <div className="relative z-10 flex flex-col items-center text-center glow-card rounded-none border border-[#1E2A45] bg-[#0C1F3D]/30 p-8">
                  <div className="w-16 h-16 rounded-none bg-[#0A1525] border border-[#1E2A45] flex items-center justify-center mb-6">
                    <span className="font-andale text-[#5fe496] text-2xl">01</span>
                  </div>
                  <h3 className="text-xl font-andale mb-3">Upload Your Design</h3>
                  <p className="text-white/70 font-avenir">
                    Upload your .STEP or .STL files to our platform. We'll analyze your design automatically.
                  </p>
                </div>

                <div className="relative z-10 flex flex-col items-center text-center glow-card rounded-none border border-[#1E2A45] bg-[#0C1F3D]/30 p-8">
                  <div className="w-16 h-16 rounded-none bg-[#0A1525] border border-[#1E2A45] flex items-center justify-center mb-6">
                    <span className="font-andale text-[#F46036] text-2xl">02</span>
                  </div>
                  <h3 className="text-xl font-andale mb-3">Get Instant Quote</h3>
                  <p className="text-white/70 font-avenir">
                    Receive an instant quote based on your design specifications. No waiting, no sales calls.
                  </p>
                </div>

                <div className="relative z-10 flex flex-col items-center text-center glow-card rounded-none border border-[#1E2A45] bg-[#0C1F3D]/30 p-8">
                  <div className="w-16 h-16 rounded-none bg-[#0A1525] border border-[#1E2A45] flex items-center justify-center mb-6">
                    <span className="font-andale text-[#1e87d6] text-2xl">03</span>
                  </div>
                  <h3 className="text-xl font-andale mb-3">Production & Delivery</h3>
                  <p className="text-white/70 font-avenir">
                    We manufacture your parts with precision and ship them directly to your door.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Services Section - Redesigned */}
      <section className="py-20 border-b border-[#1E2A45] bg-[#0A1525]">
        <div className="container px-4 md:px-6">
          <div className="max-w-5xl mx-auto">
            <div className="max-w-3xl mx-auto mb-16 flex flex-col items-center">
              <div className="inline-flex items-center rounded-none border border-[#1E2A45] bg-[#0A1525]/80 px-3 py-1 text-sm mb-4">
                <span className="text-[#5fe496] font-andale">SERVICES</span>
              </div>
              <h2 className="text-3xl font-andale tracking-tight mb-4 text-center">Industrial-Grade Manufacturing</h2>
              <p className="text-lg text-white/70 font-avenir text-center">
                High-quality production at prices that won't kill your runway.
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
              <div className="glow-card rounded-none border border-[#1E2A45] bg-[#0C1F3D]/30 p-8 transition-all duration-300 hover:bg-[#0C1F3D]/50 flex flex-col items-center text-center">
                <h3 className="text-xl font-andale mb-3 text-[#5fe496]">CNC Machining</h3>
                <p className="text-white/70 font-avenir mb-4">
                  Precision parts machined from solid blocks of material. Ideal for functional prototypes and production
                  parts.
                </p>
                <Link
                  href="/services#cnc-machining"
                  className="inline-block font-andale text-sm text-[#5fe496] border-b border-[#5fe496]/30 hover:border-[#5fe496] transition-all duration-300"
                >
                  Learn more
                </Link>
              </div>

              <div className="glow-card rounded-none border border-[#1E2A45] bg-[#0C1F3D]/30 p-8 transition-all duration-300 hover:bg-[#0C1F3D]/50 flex flex-col items-center text-center">
                <h3 className="text-xl font-andale mb-3 text-[#F46036]">3D Printing</h3>
                <p className="text-white/70 font-avenir mb-4">
                  Rapid prototyping with a range of materials. Perfect for concept validation and complex geometries.
                </p>
                <Link
                  href="/services#3d-printing"
                  className="inline-block font-andale text-sm text-[#F46036] border-b border-[#F46036]/30 hover:border-[#F46036] transition-all duration-300"
                >
                  Learn more
                </Link>
              </div>

              <div className="glow-card rounded-none border border-[#1E2A45] bg-[#0C1F3D]/30 p-8 transition-all duration-300 hover:bg-[#0C1F3D]/50 flex flex-col items-center text-center">
                <h3 className="text-xl font-andale mb-3 text-[#1e87d6]">Sheet Metal Fabrication</h3>
                <p className="text-white/70 font-avenir mb-4">
                  Custom sheet metal parts for enclosures, brackets, and structural components. Fast turnaround times.
                </p>
                <Link
                  href="/services#sheet-metal"
                  className="inline-block font-andale text-sm text-[#1e87d6] border-b border-[#1e87d6]/30 hover:border-[#1e87d6] transition-all duration-300"
                >
                  Learn more
                </Link>
              </div>
            </div>

            <div className="flex justify-center mt-12">
              <GlowButton asChild>
                <Link href="/services">View All Services</Link>
              </GlowButton>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20">
        <div className="container px-4 md:px-6">
          <div className="max-w-5xl mx-auto glow-card rounded-none bg-gradient-to-r from-[#0C1F3D]/80 to-[#0A1525]/80 border border-[#1E2A45] p-12">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-8 items-center">
              <div className="space-y-4">
                <div className="inline-flex items-center rounded-none border border-[#1E2A45] bg-[#0A1525]/80 px-3 py-1 text-sm mb-4">
                  <span className="text-[#5fe496] font-andale">GET STARTED</span>
                </div>
                <h2 className="text-3xl font-andale tracking-tight">Ready to stop overpaying?</h2>
                <p className="text-lg text-white/70 font-avenir">
                  Upload your design and get an instant quote. No sales calls, no BS.
                </p>
              </div>
              <div className="flex flex-col sm:flex-row gap-4 md:justify-end">
                <GlowButton asChild size="lg">
                  <Link href="/quote">Get Instant Quote</Link>
                </GlowButton>
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>
  )
}

