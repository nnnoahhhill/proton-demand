import { Button } from "@/components/ui/button"
import Link from "next/link"
import { Mail } from "lucide-react"

export default function AboutUsPage() {
  return (
    <div className="container px-4 md:px-6 py-12">
      <div className="max-w-4xl mx-auto">
        <div className="space-y-4 mb-12">
          <div className="inline-flex items-center rounded-md border border-[#1E2A45] bg-[#0A1525]/80 px-3 py-1 text-sm">
            <span className="text-[#5FE496] font-mono">BY FOUNDERS, FOR FOUNDERS</span>
          </div>
          <h1 className="text-3xl font-bold tracking-tight">About Us</h1>
          <p className="text-lg text-white/70">
            We're founders building for founders. Our mission is to make hardware development affordable and accessible.
          </p>
        </div>

        <div className="space-y-16">
          {/* Our Story */}
          <section>
            <h2 className="text-2xl font-bold mb-6 text-[#5FE496]">Our Story</h2>
            <div className="prose prose-invert max-w-none">
              <p className="font-mono text-white/80">
                We started proton|demand after experiencing the pain of hardware development firsthand. As founders of
                hardware startups, we were frustrated by the opacity, high costs, and slow turnaround times of
                traditional manufacturing.
              </p>
              <p className="font-mono text-white/80">
                The manufacturing industry hasn't changed in decades. It's still dominated by sales calls, PDF quotes,
                and weeks of back-and-forth. We believe hardware founders deserve better.
              </p>
              <p className="font-mono text-white/80">
                Our platform cuts through the bullshit. We provide instant quotes, transparent pricing, and rapid
                turnaround times. No sales calls, no middlemen, no markup.
              </p>
              <p className="font-mono text-white/80">
                We're building the manufacturing platform we wish existed when we were building our hardware startups.
              </p>
            </div>
          </section>

          {/* Our Mission */}
          <section>
            <h2 className="text-2xl font-bold mb-6 text-[#F46036]">Our Mission</h2>
            <div className="prose prose-invert max-w-none">
              <p className="font-mono text-white/80">
                Our mission is to democratize access to high-quality manufacturing. We believe that hardware development
                should be as accessible and iterative as software development.
              </p>
              <p className="font-mono text-white/80">
                By providing instant quotes, transparent pricing, and fast turnaround times, we're enabling founders to
                build hardware faster and more efficiently than ever before.
              </p>
              <p className="font-mono text-white/80">
                We're committed to supporting the next generation of hardware founders by removing the friction from the
                manufacturing process.
              </p>
            </div>
          </section>

          {/* Our Values */}
          <section>
            <h2 className="text-2xl font-bold mb-6 text-[#1E87D6]">Our Values</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="rounded-md border border-[#1E2A45] bg-[#0C1F3D] p-6">
                <h3 className="font-bold mb-2 text-[#5FE496]">Transparency</h3>
                <p className="text-sm text-white/70 font-mono">
                  We believe in complete transparency in pricing, processes, and communication. What you see is what you
                  get.
                </p>
              </div>
              <div className="rounded-md border border-[#1E2A45] bg-[#0C1F3D] p-6">
                <h3 className="font-bold mb-2 text-[#5FE496]">Efficiency</h3>
                <p className="text-sm text-white/70 font-mono">
                  We're obsessed with removing friction from the manufacturing process. Every step is optimized for
                  speed and simplicity.
                </p>
              </div>
              <div className="rounded-md border border-[#1E2A45] bg-[#0C1F3D] p-6">
                <h3 className="font-bold mb-2 text-[#F46036]">Quality</h3>
                <p className="text-sm text-white/70 font-mono">
                  We never compromise on quality. Every part is inspected before shipping to ensure it meets our high
                  standards.
                </p>
              </div>
              <div className="rounded-md border border-[#1E2A45] bg-[#0C1F3D] p-6">
                <h3 className="font-bold mb-2 text-[#F46036]">Founder-First</h3>
                <p className="text-sm text-white/70 font-mono">
                  We build for founders. We understand the challenges of hardware development and design our platform to
                  address them.
                </p>
              </div>
            </div>
          </section>

          {/* Contact */}
          <section className="rounded-md border border-[#1E2A45] bg-[#0C1F3D] p-8">
            <div className="text-center space-y-4">
              <h2 className="text-2xl font-bold">Get in Touch</h2>
              <p className="text-white/70 max-w-md mx-auto font-mono">
                Have questions or want to learn more about our services? We'd love to hear from you.
              </p>
              <Button asChild size="lg" className="bg-[#5FE496] hover:bg-[#5FE496]/90 text-[#0A1525] font-bold">
                <Link href="mailto:hello@protondemand.com">
                  <Mail className="mr-2 h-4 w-4" />
                  Contact Us
                </Link>
              </Button>
            </div>
          </section>
        </div>
      </div>
    </div>
  )
}

