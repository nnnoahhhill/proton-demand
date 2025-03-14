"use client"

import { useEffect, useRef } from "react"

export function BackgroundPaths() {
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = canvas.getContext("2d")
    if (!ctx) return

    // Set canvas dimensions
    const resizeCanvas = () => {
      canvas.width = window.innerWidth
      canvas.height = window.innerHeight * 3 // Make it taller to cover scrolling
    }

    resizeCanvas()
    window.addEventListener("resize", resizeCanvas)

    // Path parameters
    const paths: {
      points: { x: number; y: number }[]
      color: string
      width: number
      speed: number
      offset: number
    }[] = []

    // Create paths
    const createPaths = () => {
      paths.length = 0

      // Create 10 random paths
      for (let i = 0; i < 10; i++) {
        const numPoints = 5 + Math.floor(Math.random() * 5)
        const points = []

        // Create random points for the path
        for (let j = 0; j < numPoints; j++) {
          points.push({
            x: Math.random() * canvas.width,
            y: (canvas.height / numPoints) * j + Math.random() * 200 - 100,
          })
        }

        // Add path with random properties
        paths.push({
          points,
          color: ["#1E2A45", "#0C1F3D", "#1E87D6", "#F46036", "#5FE496"][Math.floor(Math.random() * 5)],
          width: 0.5 + Math.random() * 1.5,
          speed: 0.2 + Math.random() * 0.5,
          offset: Math.random() * 1000,
        })
      }
    }

    createPaths()

    // Animation
    let animationFrameId: number
    let lastScrollY = window.scrollY

    const render = () => {
      // Clear canvas
      ctx.clearRect(0, 0, canvas.width, canvas.height)

      // Update canvas position based on scroll
      const scrollDiff = window.scrollY - lastScrollY
      canvas.style.top = `-${window.scrollY * 0.5}px`
      lastScrollY = window.scrollY

      // Draw paths
      paths.forEach((path) => {
        ctx.beginPath()
        ctx.strokeStyle = path.color
        ctx.lineWidth = path.width
        ctx.globalAlpha = 0.1

        // Calculate time-based offset
        const timeOffset = Date.now() * path.speed * 0.001 + path.offset

        // Draw path with bezier curves
        for (let i = 0; i < path.points.length - 1; i++) {
          const current = path.points[i]
          const next = path.points[i + 1]

          // Add subtle movement based on time
          const currentX = current.x + Math.sin(timeOffset + i) * 20
          const currentY = current.y + Math.cos(timeOffset + i) * 10
          const nextX = next.x + Math.sin(timeOffset + i + 1) * 20
          const nextY = next.y + Math.cos(timeOffset + i + 1) * 10

          if (i === 0) {
            ctx.moveTo(currentX, currentY)
          }

          // Control points for bezier curve
          const cpX1 = currentX + (nextX - currentX) * 0.5
          const cpY1 = currentY
          const cpX2 = nextX - (nextX - currentX) * 0.5
          const cpY2 = nextY

          ctx.bezierCurveTo(cpX1, cpY1, cpX2, cpY2, nextX, nextY)
        }

        ctx.stroke()
      })

      animationFrameId = requestAnimationFrame(render)
    }

    render()

    return () => {
      window.removeEventListener("resize", resizeCanvas)
      cancelAnimationFrame(animationFrameId)
    }
  }, [])

  return <canvas ref={canvasRef} className="fixed top-0 left-0 w-full h-full pointer-events-none z-0 opacity-20" />
}

