import { Button } from "@/components/ui/button"
import Link from "next/link"
import { ArrowRight } from "lucide-react"

export default function MaterialsPage() {
  return (
    <div className="container px-4 md:px-6 py-12">
      <div className="max-w-4xl mx-auto">
        <div className="space-y-4 mb-12">
          <h1 className="text-3xl font-bold tracking-tight">Materials</h1>
          <p className="text-lg text-white/70">
            We offer a wide range of industrial-grade materials to meet your specific requirements.
          </p>
        </div>

        <div className="space-y-16">
          {/* Metals */}
          <section>
            <h2 className="text-2xl font-bold mb-6 flex items-center">
              <span className="h-4 w-4 rounded-full bg-bleu-de-france mr-3"></span>
              Metals
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="rounded-lg border border-white/10 bg-white/5 p-6 hover:bg-white/10 transition-colors">
                <h3 className="font-bold mb-2">Aluminum</h3>
                <p className="text-sm text-white/70 mb-4">
                  Lightweight and corrosion-resistant. Ideal for enclosures, brackets, and heat sinks.
                </p>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-white/50">Density</span>
                    <span>2.7 g/cm³</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-white/50">Tensile Strength</span>
                    <span>310 MPa</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-white/50">Finish Options</span>
                    <span>Anodized, Brushed</span>
                  </div>
                </div>
              </div>
              <div className="rounded-lg border border-white/10 bg-white/5 p-6 hover:bg-white/10 transition-colors">
                <h3 className="font-bold mb-2">Steel</h3>
                <p className="text-sm text-white/70 mb-4">
                  Strong and durable. Perfect for structural components and load-bearing parts.
                </p>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-white/50">Density</span>
                    <span>7.85 g/cm³</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-white/50">Tensile Strength</span>
                    <span>580 MPa</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-white/50">Finish Options</span>
                    <span>Zinc Plated, Powder Coated</span>
                  </div>
                </div>
              </div>
              <div className="rounded-lg border border-white/10 bg-white/5 p-6 hover:bg-white/10 transition-colors">
                <h3 className="font-bold mb-2">Titanium</h3>
                <p className="text-sm text-white/70 mb-4">
                  Exceptional strength-to-weight ratio. Ideal for aerospace and medical applications.
                </p>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-white/50">Density</span>
                    <span>4.5 g/cm³</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-white/50">Tensile Strength</span>
                    <span>950 MPa</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-white/50">Finish Options</span>
                    <span>Natural, Anodized</span>
                  </div>
                </div>
              </div>
            </div>
          </section>

          {/* Plastics */}
          <section>
            <h2 className="text-2xl font-bold mb-6 flex items-center">
              <span className="h-4 w-4 rounded-full bg-light-green mr-3"></span>
              Plastics
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="rounded-lg border border-white/10 bg-white/5 p-6 hover:bg-white/10 transition-colors">
                <h3 className="font-bold mb-2">ABS</h3>
                <p className="text-sm text-white/70 mb-4">
                  Tough and impact-resistant. Great for prototypes and functional parts.
                </p>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-white/50">Density</span>
                    <span>1.05 g/cm³</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-white/50">Heat Resistance</span>
                    <span>105°C</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-white/50">Finish Options</span>
                    <span>Matte, Glossy</span>
                  </div>
                </div>
              </div>
              <div className="rounded-lg border border-white/10 bg-white/5 p-6 hover:bg-white/10 transition-colors">
                <h3 className="font-bold mb-2">Nylon</h3>
                <p className="text-sm text-white/70 mb-4">
                  Strong and flexible. Excellent for living hinges and snap-fit assemblies.
                </p>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-white/50">Density</span>
                    <span>1.14 g/cm³</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-white/50">Heat Resistance</span>
                    <span>180°C</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-white/50">Finish Options</span>
                    <span>Natural, Dyed</span>
                  </div>
                </div>
              </div>
              <div className="rounded-lg border border-white/10 bg-white/5 p-6 hover:bg-white/10 transition-colors">
                <h3 className="font-bold mb-2">PETG</h3>
                <p className="text-sm text-white/70 mb-4">
                  Clear and chemical-resistant. Perfect for transparent parts and enclosures.
                </p>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-white/50">Density</span>
                    <span>1.27 g/cm³</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-white/50">Heat Resistance</span>
                    <span>70°C</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-white/50">Finish Options</span>
                    <span>Clear, Polished</span>
                  </div>
                </div>
              </div>
            </div>
          </section>

          {/* Elastomers */}
          <section>
            <h2 className="text-2xl font-bold mb-6 flex items-center">
              <span className="h-4 w-4 rounded-full bg-giants-orange mr-3"></span>
              Elastomers
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="rounded-lg border border-white/10 bg-white/5 p-6 hover:bg-white/10 transition-colors">
                <h3 className="font-bold mb-2">TPU</h3>
                <p className="text-sm text-white/70 mb-4">
                  Flexible and durable. Ideal for gaskets, seals, and protective covers.
                </p>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-white/50">Hardness</span>
                    <span>85A Shore</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-white/50">Elongation</span>
                    <span>580%</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-white/50">Finish Options</span>
                    <span>Matte</span>
                  </div>
                </div>
              </div>
              <div className="rounded-lg border border-white/10 bg-white/5 p-6 hover:bg-white/10 transition-colors">
                <h3 className="font-bold mb-2">Silicone</h3>
                <p className="text-sm text-white/70 mb-4">
                  Heat-resistant and biocompatible. Perfect for medical devices and food-safe applications.
                </p>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-white/50">Hardness</span>
                    <span>40-70A Shore</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-white/50">Heat Resistance</span>
                    <span>250°C</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-white/50">Finish Options</span>
                    <span>Smooth, Textured</span>
                  </div>
                </div>
              </div>
            </div>
          </section>

          {/* CTA */}
          <div className="rounded-lg border border-white/10 bg-gradient-to-br from-oxford-blue to-oxford-blue/50 p-8 text-center">
            <h2 className="text-2xl font-bold mb-4">Not sure which material is right for your project?</h2>
            <p className="text-white/70 max-w-md mx-auto mb-6">
              Upload your model and our system will recommend the best materials based on your requirements.
            </p>
            <Button asChild size="lg" className="bg-bleu-de-france hover:bg-bleu-de-france/90">
              <Link href="/upload">
                Upload Model
                <ArrowRight className="ml-2 h-4 w-4" />
              </Link>
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}

