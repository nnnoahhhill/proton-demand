import Link from "next/link"
import { GlowButton } from "@/components/ui/glow-button"
import { Check } from "lucide-react"

export default function ServicesPage() {
  return (
    <div className="container px-4 md:px-6 py-12">
      <div className="max-w-6xl mx-auto">
        <div className="space-y-4 mb-12">
          <div className="inline-flex items-center rounded-none border border-[#1E2A45] bg-[#0A1525]/80 px-3 py-1 text-sm">
            <span className="text-[#5fe496] font-andale">SERVICES</span>
          </div>
          <h1 className="text-3xl font-andale tracking-tight">Our Services</h1>
        </div>

        <div className="grid grid-cols-1 gap-8">
          {/* CNC Machining */}
          <div className="glow-card rounded-none border border-[#1E2A45] bg-[#0A1525]/50 overflow-hidden">
            <div className="p-8 flex flex-col items-center text-center">
              <div className="space-y-4 max-w-3xl mx-auto">
                <h2 className="text-3xl font-andale text-[#5fe496]">CNC Machining</h2>
                <p className="text-xl text-white/70 font-avenir">Precision machined parts with tight tolerances</p>

                <div className="space-y-6 mt-6">
                  <div>
                    <h3 className="text-lg font-andale text-[#F46036] mb-3">Materials</h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div className="space-y-4">
                        <div>
                          <div className="flex items-center justify-center mb-2">
                            <Check className="h-5 w-5 text-[#5fe496] mr-2" />
                            <span className="text-base font-medium text-white/90 font-avenir">Metal</span>
                          </div>
                          <div className="space-y-1.5">
                            <div className="text-center text-white/70 font-avenir">
                              Aluminum 6061, Mild Steel, 304 Stainless Steel, 316 Stainless Steel, Titanium, Copper,
                              Brass
                            </div>
                          </div>
                        </div>
                      </div>
                      <div className="space-y-4">
                        <div>
                          <div className="flex items-center justify-center mb-2">
                            <Check className="h-5 w-5 text-[#5fe496] mr-2" />
                            <span className="text-base font-medium text-white/90 font-avenir">Plastic</span>
                          </div>
                          <div className="space-y-1.5">
                            <div className="text-center text-white/70 font-avenir">
                              HDPE, POM (Acetal), ABS, Acrylic, Nylon, PEEK, PC
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div>
                    <h3 className="text-lg font-andale text-[#F46036] mb-3">Capabilities</h3>
                    <div className="space-y-1.5">
                      <div className="flex items-center justify-center">
                        <Check className="h-5 w-5 text-[#5fe496] mr-2" />
                        <span className="text-base text-white/70 font-avenir">Tight tolerances (±0.05mm)</span>
                      </div>
                      <div className="flex items-center justify-center">
                        <Check className="h-5 w-5 text-[#5fe496] mr-2" />
                        <span className="text-base text-white/70 font-avenir">Complex geometries</span>
                      </div>
                      <div className="flex items-center justify-center">
                        <Check className="h-5 w-5 text-[#5fe496] mr-2" />
                        <span className="text-base text-white/70 font-avenir">Quick turnaround times</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <GlowButton asChild className="mt-8">
                <Link href="/quote">Get Instant Quote</Link>
              </GlowButton>
            </div>
          </div>

          {/* 3D Printing */}
          <div className="glow-card rounded-none border border-[#1E2A45] bg-[#0A1525]/50 overflow-hidden">
            <div className="p-8 flex flex-col items-center text-center">
              <div className="space-y-4 max-w-3xl mx-auto">
                <h2 className="text-3xl font-andale text-[#F46036]">3D Printing</h2>
                <p className="text-xl text-white/70 font-avenir">Rapid prototyping and low-volume production</p>

                <div className="space-y-6 mt-6">
                  <div>
                    <h3 className="text-lg font-andale text-[#F46036] mb-3">Materials</h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div className="space-y-4">
                        <div>
                          <div className="flex items-center justify-center mb-2">
                            <Check className="h-5 w-5 text-[#5fe496] mr-2" />
                            <span className="text-base font-medium text-white/90 font-avenir">FDM Materials</span>
                          </div>
                          <div className="space-y-1.5">
                            <div className="text-center text-white/70 font-avenir">
                              PLA, ABS, Nylon 12, ASA, PETG, TPU
                            </div>
                          </div>
                        </div>
                      </div>
                      <div className="space-y-4">
                        <div>
                          <div className="flex items-center justify-center mb-2">
                            <Check className="h-5 w-5 text-[#5fe496] mr-2" />
                            <span className="text-base font-medium text-white/90 font-avenir">SLA/SLS Materials</span>
                          </div>
                          <div className="space-y-1.5">
                            <div className="text-center text-white/70 font-avenir">
                              Standard Resin, Nylon 12 White, Nylon 12 Black
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div>
                    <h3 className="text-lg font-andale text-[#F46036] mb-3">Capabilities</h3>
                    <div className="space-y-1.5">
                      <div className="flex items-center justify-center">
                        <Check className="h-5 w-5 text-[#5fe496] mr-2" />
                        <span className="text-base text-white/70 font-avenir">FDM, SLS, and SLA technologies</span>
                      </div>
                      <div className="flex items-center justify-center">
                        <Check className="h-5 w-5 text-[#5fe496] mr-2" />
                        <span className="text-base text-white/70 font-avenir">
                          Complex geometries with no tooling costs
                        </span>
                      </div>
                      <div className="flex items-center justify-center">
                        <Check className="h-5 w-5 text-[#5fe496] mr-2" />
                        <span className="text-base text-white/70 font-avenir">Rapid turnaround for prototypes</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <GlowButton asChild className="mt-8">
                <Link href="/quote">Get Instant Quote</Link>
              </GlowButton>
            </div>
          </div>

          {/* Sheet Metal */}
          <div className="glow-card rounded-none border border-[#1E2A45] bg-[#0A1525]/50 overflow-hidden">
            <div className="p-8 flex flex-col items-center text-center">
              <div className="space-y-4 max-w-3xl mx-auto">
                <h2 className="text-3xl font-andale text-[#1e87d6]">Sheet Metal Fabrication</h2>
                <p className="text-xl text-white/70 font-avenir">Custom fabrication for your projects</p>

                <div className="space-y-6 mt-6">
                  <div>
                    <h3 className="text-lg font-andale text-[#F46036] mb-3">Materials</h3>
                    <div className="space-y-1.5">
                      <div className="text-center text-white/70 font-avenir">
                        Aluminum 6061, Mild Steel, 304 Stainless Steel, 316 Stainless Steel, Titanium, Copper, Brass
                      </div>
                    </div>
                  </div>

                  <div>
                    <h3 className="text-lg font-andale text-[#F46036] mb-3">Capabilities</h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div className="space-y-1.5">
                        <div className="flex items-center justify-center">
                          <Check className="h-5 w-5 text-[#5fe496] mr-2" />
                          <span className="text-base text-white/70 font-avenir">Laser Cutting</span>
                        </div>
                        <div className="flex items-center justify-center">
                          <Check className="h-5 w-5 text-[#5fe496] mr-2" />
                          <span className="text-base text-white/70 font-avenir">Bending</span>
                        </div>
                        <div className="flex items-center justify-center">
                          <Check className="h-5 w-5 text-[#5fe496] mr-2" />
                          <span className="text-base text-white/70 font-avenir">Welding</span>
                        </div>
                      </div>
                      <div className="space-y-1.5">
                        <div className="flex items-center justify-center">
                          <Check className="h-5 w-5 text-[#5fe496] mr-2" />
                          <span className="text-base text-white/70 font-avenir">Punching</span>
                        </div>
                        <div className="flex items-center justify-center">
                          <Check className="h-5 w-5 text-[#5fe496] mr-2" />
                          <span className="text-base text-white/70 font-avenir">Riveting</span>
                        </div>
                        <div className="flex items-center justify-center">
                          <Check className="h-5 w-5 text-[#5fe496] mr-2" />
                          <span className="text-base text-white/70 font-avenir">Stamping</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <GlowButton asChild className="mt-8">
                <Link href="/quote">Get Instant Quote</Link>
              </GlowButton>
            </div>
          </div>
        </div>

        <div className="flex justify-center mt-12">
          <GlowButton asChild size="lg">
            <Link href="/quote">Get Started Now</Link>
          </GlowButton>
        </div>
      </div>
    </div>
  )
}

