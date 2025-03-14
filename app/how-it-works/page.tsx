import { Button } from "@/components/ui/button"
import Link from "next/link"
import { ArrowRight, Upload, Settings, Truck, CheckCircle } from "lucide-react"

export default function HowItWorksPage() {
  return (
    <div className="container px-4 md:px-6 py-12">
      <div className="max-w-4xl mx-auto">
        <div className="space-y-4 mb-12">
          <h1 className="text-3xl font-bold tracking-tight">How It Works</h1>
          <p className="text-lg text-white/70">
            We've stripped away the complexity from manufacturing. Here's our straightforward process.
          </p>
        </div>

        <div className="space-y-16">
          {/* Step 1 */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8 items-center">
            <div className="space-y-4">
              <div className="inline-flex items-center justify-center h-12 w-12 rounded-full bg-bleu-de-france/10 text-bleu-de-france">
                <Upload className="h-6 w-6" />
              </div>
              <h2 className="text-2xl font-bold">1. Upload Your Model</h2>
              <p className="text-white/70">
                Simply drag and drop your 3D model file. We support all major CAD formats including .STL, .STEP, .IGES,
                .OBJ, .GLB, and more.
              </p>
            </div>
            <div className="rounded-lg border border-white/10 bg-white/5 aspect-video flex items-center justify-center">
              <span className="font-mono text-white/30 text-sm">Upload Visualization</span>
            </div>
          </div>

          {/* Step 2 */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8 items-center">
            <div className="order-2 md:order-1 rounded-lg border border-white/10 bg-white/5 aspect-video flex items-center justify-center">
              <span className="font-mono text-white/30 text-sm">Options Visualization</span>
            </div>
            <div className="order-1 md:order-2 space-y-4">
              <div className="inline-flex items-center justify-center h-12 w-12 rounded-full bg-light-green/10 text-light-green">
                <Settings className="h-6 w-6" />
              </div>
              <h2 className="text-2xl font-bold">2. Select Options</h2>
              <p className="text-white/70">
                Choose your manufacturing process, material, finish, and quantity. Our platform provides real-time
                feedback on manufacturability.
              </p>
            </div>
          </div>

          {/* Step 3 */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8 items-center">
            <div className="space-y-4">
              <div className="inline-flex items-center justify-center h-12 w-12 rounded-full bg-giants-orange/10 text-giants-orange">
                <Truck className="h-6 w-6" />
              </div>
              <h2 className="text-2xl font-bold">3. Production & Delivery</h2>
              <p className="text-white/70">
                Once you approve the quote, we handle the rest. Your parts are manufactured to spec and shipped directly
                to your door.
              </p>
            </div>
            <div className="rounded-lg border border-white/10 bg-white/5 aspect-video flex items-center justify-center">
              <span className="font-mono text-white/30 text-sm">Production Visualization</span>
            </div>
          </div>

          {/* Benefits */}
          <div className="rounded-lg border border-white/10 bg-gradient-to-br from-oxford-blue to-oxford-blue/50 p-8">
            <h2 className="text-2xl font-bold mb-6">Why Choose proton|demand</h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
              <div className="flex items-start space-x-4">
                <CheckCircle className="h-6 w-6 text-light-green flex-shrink-0 mt-1" />
                <div>
                  <h3 className="font-medium">No Middlemen</h3>
                  <p className="text-sm text-white/70">
                    Direct access to manufacturing capacity means lower costs for you.
                  </p>
                </div>
              </div>
              <div className="flex items-start space-x-4">
                <CheckCircle className="h-6 w-6 text-light-green flex-shrink-0 mt-1" />
                <div>
                  <h3 className="font-medium">Transparent Pricing</h3>
                  <p className="text-sm text-white/70">See exactly what you're paying for with line-item breakdowns.</p>
                </div>
              </div>
              <div className="flex items-start space-x-4">
                <CheckCircle className="h-6 w-6 text-light-green flex-shrink-0 mt-1" />
                <div>
                  <h3 className="font-medium">Rapid Turnaround</h3>
                  <p className="text-sm text-white/70">Get parts in days, not weeks or months.</p>
                </div>
              </div>
              <div className="flex items-start space-x-4">
                <CheckCircle className="h-6 w-6 text-light-green flex-shrink-0 mt-1" />
                <div>
                  <h3 className="font-medium">Quality Guaranteed</h3>
                  <p className="text-sm text-white/70">Every part is inspected before shipping.</p>
                </div>
              </div>
            </div>
          </div>

          {/* CTA */}
          <div className="text-center space-y-6">
            <h2 className="text-2xl font-bold">Ready to get started?</h2>
            <p className="text-white/70 max-w-md mx-auto">
              Upload your model now and experience manufacturing without the bullshit.
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

