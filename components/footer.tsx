import Link from "next/link"
import Image from "next/image"

export function Footer() {
  return (
    <footer className="border-t border-[#1E2A45] bg-[#0A1525]">
      <div className="container px-4 md:px-6 py-12">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          <div className="space-y-4">
            <Link href="/" className="flex items-center">
              <Image
                src="/brand_assets/PD_dark_horizontal.svg"
                alt="proton|demand logo"
                width={180}
                height={40}
                className="h-8 w-auto"
              />
            </Link>
            <p className="text-sm text-white/70 font-avenir">Pay less. Build more.</p>
          </div>
          <div>
            <h3 className="text-sm font-andale mb-4 text-[#F46036]">Services</h3>
            <ul className="space-y-3 font-avenir">
              <li>
                <Link
                  href="/services#cnc-machining"
                  className="text-sm text-white/70 hover:text-[#F46036] transition-colors"
                >
                  CNC Machining
                </Link>
              </li>
              <li>
                <Link
                  href="/services#3d-printing"
                  className="text-sm text-white/70 hover:text-[#F46036] transition-colors"
                >
                  3D Printing
                </Link>
              </li>
              <li>
                <Link
                  href="/services#sheet-metal"
                  className="text-sm text-white/70 hover:text-[#F46036] transition-colors"
                >
                  Sheet Metal Fabrication
                </Link>
              </li>
            </ul>
          </div>
          <div>
            <h3 className="text-sm font-andale mb-4 text-[#F46036]">Company</h3>
            <ul className="space-y-3 font-avenir">
              <li>
                <Link href="/about-us" className="text-sm text-white/70 hover:text-[#F46036] transition-colors">
                  About Us
                </Link>
              </li>
              <li>
                <Link href="/contact" className="text-sm text-white/70 hover:text-[#F46036] transition-colors">
                  Contact
                </Link>
              </li>
              <li>
                <Link href="/terms" className="text-sm text-white/70 hover:text-[#F46036] transition-colors">
                  Terms & Privacy
                </Link>
              </li>
            </ul>
          </div>
        </div>
        <div className="mt-12 pt-8 border-t border-[#1E2A45]">
          <div className="flex flex-col md:flex-row justify-between items-center">
            <p className="text-sm text-white/50 font-avenir">
              © {new Date().getFullYear()} proton|demand. All rights reserved.
            </p>
            <div className="flex items-center space-x-4 mt-4 md:mt-0">
              <span className="text-xs text-white/30 font-avenir">By founders, for founders</span>
            </div>
          </div>
        </div>
      </div>
    </footer>
  )
}

