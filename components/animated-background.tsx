"use client"

import { useEffect, useRef } from "react"

export function AnimatedBackground() {
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
      speed: number
      progress: number
      width: number
      color: string
    }[] = []

    // Create random paths
    for (let i = 0; i < 15; i++) {
      const numPoints = Math.floor(Math.random() * 3) + 2
      const points = []

      for (let j = 0; j < numPoints; j++) {
        points.push({
          x: Math.random() * canvas.width,
          y: Math.random() * canvas.height,
        })
      }

      paths.push({
        points,
        speed: 0.0005 + Math.random() * 0.001,
        progress: Math.random(),
        width: Math.random() * 1 + 0.5,
        color: `rgba(255, 255, 255, ${Math.random() * 0.1 + 0.05})`,
      })
    }

    // Animation function
    const animate = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height)

      // Apply scroll offset
      const scrollY = window.scrollY
      ctx.setTransform(1, 0, 0, 1, 0, -scrollY * 0.5)

      // Draw paths
      for (const path of paths) {
        ctx.beginPath()
        ctx.strokeStyle = path.color
        ctx.lineWidth = path.width

        // Update progress
        path.progress += path.speed
        if (path.progress > 1) path.progress = 0

        // Calculate current position along the path
        const currentPoint = getPointOnPath(path.points, path.progress)

        ctx.moveTo(currentPoint.x, currentPoint.y)

        // Draw line to next points
        for (let i = 1; i <= 50; i++) {
          const progress = (path.progress + i * 0.01) % 1
          const point = getPointOnPath(path.points, progress)
          ctx.lineTo(point.x, point.y)
        }

        ctx.stroke()
      }

      requestAnimationFrame(animate)
    }

    // Helper function to get point on a path
    const getPointOnPath = (points: { x: number; y: number }[], progress: number) => {
      if (points.length === 1) return points[0]

      const numSegments = points.length - 1
      const segment = Math.floor(progress * numSegments)
      const segmentProgress = (progress * numSegments) % 1

      const start = points[segment]
      const end = points[(segment + 1) % points.length]

      return {
        x: start.x + (end.x - start.x) * segmentProgress,
        y: start.y + (end.y - start.y) * segmentProgress,
      }
    }

    animate()

    return () => {
      window.removeEventListener("resize", resizeCanvas)
    }
  }, [])

  return <canvas ref={canvasRef} className="fixed top-0 left-0 w-full h-full pointer-events-none opacity-10 z-0" />
}

