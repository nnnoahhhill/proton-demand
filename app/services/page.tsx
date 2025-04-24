import Link from "next/link"
import { GlowButton } from "@/components/ui/glow-button"
import { Check } from "lucide-react"

export default function ServicesPage() {
  return (
    <div className="container px-4 md:px-6 py-12 max-w-7xl mx-auto">
      <div className="max-w-6xl mx-auto">
        <div className="space-y-4 mb-12">
          <div className="inline-flex items-center rounded-none border border-[#1E2A45] bg-[#0A1525]/80 px-3 py-1 text-sm">
            <span className="text-[#5fe496] font-andale">SERVICES</span>
          </div>
          <h1 className="text-3xl font-andale tracking-tight">Our Services</h1>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-12">
          {/* CNC Machining */}
          <div id="cnc-machining" className="glow-card rounded-none border-2 border-[#5fe496]/30 bg-[#0A1525]/50 overflow-hidden h-full flex flex-col">
            <div className="p-8 flex flex-col text-left flex-grow">
              <div className="space-y-4 w-full">
                <h2 className="text-2xl font-andale text-[#5fe496] text-left">CNC Machining</h2>
                <p className="text-lg text-white/70 font-avenir">Precision machined parts with tight tolerances</p>

                <div className="space-y-6 mt-6">
                  <div>
                    <h3 className="text-lg font-andale text-[#5fe496] mb-3">Materials</h3>
                    <div className="grid grid-cols-1 gap-4">
                      <div>
                        <div className="flex items-center mb-2">
                          <Check className="h-5 w-5 text-[#5fe496] mr-2" />
                          <span className="text-base font-medium text-white/90 font-avenir">Metal</span>
                        </div>
                        <div className="text-left text-white/70 font-avenir text-sm">
                          Aluminum 6061, Mild Steel, 304/316 Stainless Steel, Titanium, Copper, Brass
                        </div>
                      </div>
                      <div>
                        <div className="flex items-center mb-2">
                          <Check className="h-5 w-5 text-[#5fe496] mr-2" />
                          <span className="text-base font-medium text-white/90 font-avenir">Plastic</span>
                        </div>
                        <div className="text-left text-white/70 font-avenir text-sm">
                          HDPE, POM (Acetal), ABS, Acrylic, Nylon, PEEK, PC
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="mt-8">
                    <h3 className="text-lg font-andale text-[#5fe496] mb-3">Capabilities</h3>
                    <div className="space-y-1.5">
                      <div className="flex items-center">
                        <Check className="h-5 w-5 text-[#5fe496] mr-2" />
                        <span className="text-sm text-white/70 font-avenir">Tight tolerances (±0.05mm)</span>
                      </div>
                      <div className="flex items-center">
                        <Check className="h-5 w-5 text-[#5fe496] mr-2" />
                        <span className="text-sm text-white/70 font-avenir">Complex geometries</span>
                      </div>
                      <div className="flex items-center">
                        <Check className="h-5 w-5 text-[#5fe496] mr-2" />
                        <span className="text-sm text-white/70 font-avenir">Quick turnaround times</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <div className="mt-auto pt-10 flex justify-center">
                <GlowButton asChild>
                  <Link href="/quote">Get Instant Quote</Link>
                </GlowButton>
              </div>
            </div>
          </div>

          {/* 3D Printing */}
          <div id="3d-printing" className="glow-card rounded-none border-2 border-[#F46036]/30 bg-[#0A1525]/50 overflow-hidden h-full flex flex-col">
            <div className="p-8 flex flex-col text-left flex-grow">
              <div className="space-y-4 w-full">
                <h2 className="text-2xl font-andale text-[#F46036] text-left">3D Printing</h2>
                <p className="text-lg text-white/70 font-avenir">Rapid prototyping and low-volume production</p>

                <div className="space-y-6 mt-6">
                  <div>
                    <h3 className="text-lg font-andale text-[#F46036] mb-3">Materials</h3>
                    <div className="grid grid-cols-1 gap-4">
                      <div>
                        <div className="flex items-center mb-2">
                          <Check className="h-5 w-5 text-[#5fe496] mr-2" />
                          <span className="text-base font-medium text-white/90 font-avenir">FDM Materials</span>
                        </div>
                        <div className="text-left text-white/70 font-avenir text-sm">
                          PLA, ABS, Nylon 12, ASA, PETG, TPU
                        </div>
                      </div>
                      <div>
                        <div className="flex items-center mb-2">
                          <Check className="h-5 w-5 text-[#5fe496] mr-2" />
                          <span className="text-base font-medium text-white/90 font-avenir">SLA/SLS Materials</span>
                        </div>
                        <div className="text-left text-white/70 font-avenir text-sm">
                          Standard Resin, Nylon 12 White, Nylon 12 Black
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="mt-8">
                    <h3 className="text-lg font-andale text-[#F46036] mb-3">Capabilities</h3>
                    <div className="space-y-1.5">
                      <div className="flex items-center">
                        <Check className="h-5 w-5 text-[#5fe496] mr-2" />
                        <span className="text-sm text-white/70 font-avenir">FDM, SLS, and SLA technologies</span>
                      </div>
                      <div className="flex items-center">
                        <Check className="h-5 w-5 text-[#5fe496] mr-2" />
                        <span className="text-sm text-white/70 font-avenir">Complex geometries with no tooling costs</span>
                      </div>
                      <div className="flex items-center">
                        <Check className="h-5 w-5 text-[#5fe496] mr-2" />
                        <span className="text-sm text-white/70 font-avenir">Rapid turnaround for prototypes</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <div className="mt-auto pt-10 flex justify-center">
                <GlowButton asChild>
                  <Link href="/quote">Get Instant Quote</Link>
                </GlowButton>
              </div>
            </div>
          </div>

          {/* Sheet Metal */}
          <div id="sheet-metal" className="glow-card rounded-none border-2 border-[#1e87d6]/30 bg-[#0A1525]/50 overflow-hidden h-full flex flex-col">
            <div className="p-8 flex flex-col text-left flex-grow">
              <div className="space-y-4 w-full">
                <h2 className="text-2xl font-andale text-[#1e87d6] text-left">Sheet Metal Fab</h2>
                <p className="text-lg text-white/70 font-avenir">Custom fabrication for your projects</p>

                <div className="space-y-6 mt-6">
                  <div>
                    <h3 className="text-lg font-andale text-[#1e87d6] mb-3">Materials</h3>
                    <div className="grid grid-cols-2 gap-2">
                      <div>
                        <div className="flex items-center mb-2">
                          <Check className="h-5 w-5 text-[#5fe496] mr-2" />
                          <span className="text-base font-medium text-white/90 font-avenir">Aluminum</span>
                        </div>
                      </div>
                      <div>
                        <div className="flex items-center mb-2">
                          <Check className="h-5 w-5 text-[#5fe496] mr-2" />
                          <span className="text-base font-medium text-white/90 font-avenir">Steel</span>
                        </div>
                      </div>
                      <div>
                        <div className="flex items-center mb-2">
                          <Check className="h-5 w-5 text-[#5fe496] mr-2" />
                          <span className="text-base font-medium text-white/90 font-avenir">Stainless</span>
                        </div>
                      </div>
                      <div>
                        <div className="flex items-center mb-2">
                          <Check className="h-5 w-5 text-[#5fe496] mr-2" />
                          <span className="text-base font-medium text-white/90 font-avenir">Copper/Brass</span>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="mt-8">
                    <h3 className="text-lg font-andale text-[#1e87d6] mb-3">Capabilities</h3>
                    <div className="grid grid-cols-2 gap-1">
                      <div className="flex items-center">
                        <Check className="h-5 w-5 text-[#5fe496] mr-2" />
                        <span className="text-sm text-white/70 font-avenir">Laser Cutting</span>
                      </div>
                      <div className="flex items-center">
                        <Check className="h-5 w-5 text-[#5fe496] mr-2" />
                        <span className="text-sm text-white/70 font-avenir">Punching</span>
                      </div>
                      <div className="flex items-center">
                        <Check className="h-5 w-5 text-[#5fe496] mr-2" />
                        <span className="text-sm text-white/70 font-avenir">Bending</span>
                      </div>
                      <div className="flex items-center">
                        <Check className="h-5 w-5 text-[#5fe496] mr-2" />
                        <span className="text-sm text-white/70 font-avenir">Riveting</span>
                      </div>
                      <div className="flex items-center">
                        <Check className="h-5 w-5 text-[#5fe496] mr-2" />
                        <span className="text-sm text-white/70 font-avenir">Welding</span>
                      </div>
                      <div className="flex items-center">
                        <Check className="h-5 w-5 text-[#5fe496] mr-2" />
                        <span className="text-sm text-white/70 font-avenir">Stamping</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <div className="mt-auto pt-10 flex justify-center">
                <GlowButton asChild>
                  <Link href="/quote">Get Instant Quote</Link>
                </GlowButton>
              </div>
            </div>
          </div>
        </div>


      </div>
    </div>
  )
}

