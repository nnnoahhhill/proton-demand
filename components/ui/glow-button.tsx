import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/lib/utils"

const glowButtonVariants = cva(
  "inline-flex items-center justify-center whitespace-nowrap font-andale rounded-none border px-4 py-2 text-sm font-medium transition-all focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-white disabled:pointer-events-none disabled:opacity-50 glow-button",
  {
    variants: {
      variant: {
        default: "bg-[#5fe496] text-[#0a1525] hover:bg-[#F46036] hover:text-white border-[#5fe496] font-bold",
        orange: "bg-[#F46036] text-white hover:bg-[#F46036]/90 border-[#F46036]",
        blue: "bg-[#1e87d6] text-white hover:bg-[#1e87d6]/90 border-[#1e87d6]",
        outline: "bg-transparent border-white/10 hover:bg-[#5fe496] hover:text-[#0a1525]",
      },
      size: {
        default: "h-9 px-4 py-2",
        sm: "h-8 px-3 text-xs",
        lg: "h-10 px-6 text-base",
        icon: "h-9 w-9",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  },
)

export interface GlowButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof glowButtonVariants> {
  asChild?: boolean
}

const GlowButton = React.forwardRef<HTMLButtonElement, GlowButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    return <button className={cn(glowButtonVariants({ variant, size, className }))} ref={ref} {...props} />
  },
)
GlowButton.displayName = "GlowButton"

export { GlowButton, glowButtonVariants }

