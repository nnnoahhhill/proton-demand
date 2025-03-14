import { Button } from "@/components/ui/button"
import Link from "next/link"
import { Mail } from "lucide-react"

export default function AboutPage() {
  return (
    <div className="container px-4 md:px-6 py-12">
      <div className="max-w-4xl mx-auto">
        <div className="space-y-4 mb-12">
          <h1 className="text-3xl font-bold tracking-tight">About proton|demand</h1>
          <p className="text-lg text-white/70">
            We're founders building for founders. Our mission is to make hardware development as frictionless as
            software.
          </p>
        </div>

        <div className="space-y-16">
          {/* Our Story */}
          <section>
            <h2 className="text-2xl font-bold mb-6">Our Story</h2>
            <div className="prose prose-invert max-w-none">
              <p>
                We started proton|demand after experiencing the pain of hardware development firsthand. As founders of
                hardware startups, we were frustrated by the opacity, high costs, and slow turnaround times of
                traditional manufacturing.
              </p>
              <p>
                The manufacturing industry hasn't changed in decades. It's still dominated by sales calls, PDF quotes,
                and weeks of back-and-forth. We believe hardware founders deserve better.
              </p>
              <p>
                Our platform cuts through the bullshit. We provide instant quotes, transparent pricing, and rapid
                turnaround times. No sales calls, no middlemen, no markup.
              </p>
              <p>
                We're building the manufacturing platform we wish existed when we were building our hardware startups.
              </p>
            </div>
          </section>

          {/* Our Values */}
          <section>
            <h2 className="text-2xl font-bold mb-6">Our Values</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="rounded-lg border border-white/10 bg-white/5 p-6">
                <h3 className="font-bold mb-2">Transparency</h3>
                <p className="text-sm text-white/70">
                  We believe in complete transparency in pricing, processes, and communication. What you see is what you
                  get.
                </p>
              </div>
              <div className="rounded-lg border border-white/10 bg-white/5 p-6">
                <h3 className="font-bold mb-2">Efficiency</h3>
                <p className="text-sm text-white/70">
                  We're obsessed with removing friction from the manufacturing process. Every step is optimized for
                  speed and simplicity.
                </p>
              </div>
              <div className="rounded-lg border border-white/10 bg-white/5 p-6">
                <h3 className="font-bold mb-2">Quality</h3>
                <p className="text-sm text-white/70">
                  We never compromise on quality. Every part is inspected before shipping to ensure it meets our high
                  standards.
                </p>
              </div>
              <div className="rounded-lg border border-white/10 bg-white/5 p-6">
                <h3 className="font-bold mb-2">Founder-First</h3>
                <p className="text-sm text-white/70">
                  We build for founders. We understand the challenges of hardware development and design our platform to
                  address them.
                </p>
              </div>
            </div>
          </section>

          {/* Team */}
          <section>
            <h2 className="text-2xl font-bold mb-6">Our Team</h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="rounded-lg border border-white/10 bg-white/5 p-6 text-center">
                <div className="w-24 h-24 rounded-full bg-gradient-to-br from-bleu-de-france/20 to-bleu-de-france/5 mx-auto mb-4"></div>
                <h3 className="font-bold">Alex Chen</h3>
                <p className="text-sm text-white/70 mb-2">CEO & Co-Founder</p>
                <p className="text-xs text-white/50">Former hardware founder with 10+ years in manufacturing.</p>
              </div>
              <div className="rounded-lg border border-white/10 bg-white/5 p-6 text-center">
                <div className="w-24 h-24 rounded-full bg-gradient-to-br from-light-green/20 to-light-green/5 mx-auto mb-4"></div>
                <h3 className="font-bold">Sarah Johnson</h3>
                <p className="text-sm text-white/70 mb-2">CTO & Co-Founder</p>
                <p className="text-xs text-white/50">Mechanical engineer with expertise in advanced manufacturing.</p>
              </div>
              <div className="rounded-lg border border-white/10 bg-white/5 p-6 text-center">
                <div className="w-24 h-24 rounded-full bg-gradient-to-br from-giants-orange/20 to-giants-orange/5 mx-auto mb-4"></div>
                <h3 className="font-bold">Michael Lee</h3>
                <p className="text-sm text-white/70 mb-2">Head of Operations</p>
                <p className="text-xs text-white/50">
                  Supply chain expert with experience at leading hardware companies.
                </p>
              </div>
            </div>
          </section>

          {/* Contact */}
          <section className="rounded-lg border border-white/10 bg-gradient-to-br from-oxford-blue to-oxford-blue/50 p-8">
            <div className="text-center space-y-4">
              <h2 className="text-2xl font-bold">Get in Touch</h2>
              <p className="text-white/70 max-w-md mx-auto">
                Have questions or want to learn more about our services? We'd love to hear from you.
              </p>
              <Button asChild size="lg" className="bg-bleu-de-france hover:bg-bleu-de-france/90">
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

