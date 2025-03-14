"use client"

import { useEffect, useState } from "react"
import { Canvas } from "@react-three/fiber"
import { OrbitControls, Environment } from "@react-three/drei"
import { STLLoader } from "three/examples/jsm/loaders/STLLoader.js"
import * as THREE from "three"

interface ModelViewerProps {
  file?: File
  url?: string
  autoRotate?: boolean
  interactive?: boolean
  showGrid?: boolean
  className?: string
}

export function ModelViewer({
  file,
  url,
  autoRotate = true,
  interactive = true,
  showGrid = false,
  className = "w-full h-full",
}: ModelViewerProps) {
  const [geometry, setGeometry] = useState<THREE.BufferGeometry | null>(null)
  const [normalizedScale, setNormalizedScale] = useState<number>(1)
  const [loading, setLoading] = useState<boolean>(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!file && !url) {
      setLoading(false)
      return
    }

    const fileUrl = file ? URL.createObjectURL(file) : url
    const fileType = file ? file.name.split(".").pop()?.toLowerCase() : url?.split(".").pop()?.toLowerCase()

    if (fileType === "stl") {
      setLoading(true)
      setError(null)

      try {
        const loader = new STLLoader()
        loader.load(
          fileUrl as string,
          (geometry: THREE.BufferGeometry) => {
            try {
              // Center the model
              geometry.computeBoundingBox()
              const center = new THREE.Vector3()
              geometry.boundingBox!.getCenter(center)
              geometry.translate(-center.x, -center.y, -center.z)

              // Calculate normalized scale to ensure consistent sizing
              const size = new THREE.Vector3()
              geometry.boundingBox!.getSize(size)
              const maxDim = Math.max(size.x, size.y, size.z)
              
              // Use a consistent target size for all models
              const targetSize = 2
              const calculatedScale = targetSize / maxDim
              
              setNormalizedScale(calculatedScale)
              setGeometry(geometry)
              setLoading(false)
            } catch (err) {
              console.error("Error processing geometry:", err)
              setError("Failed to process the model. Please try again.")
              setLoading(false)
            }
          },
          undefined,
          (err: any) => {
            console.error("Error loading STL:", err)
            setError("Failed to load the model. Please try again.")
            setLoading(false)
          },
        )
      } catch (err) {
        console.error("Exception in STL loading:", err)
        setError("Failed to load the model. Please try again.")
        setLoading(false)
      }
    } else if (fileType === "step" || fileType === "stp") {
      setError("STEP file support is coming soon. Please use STL files for now.")
      setLoading(false)
    } else {
      setError("Unsupported file format. Please upload an STL or STEP file.")
      setLoading(false)
    }

    return () => {
      if (file && fileUrl) {
        URL.revokeObjectURL(fileUrl)
      }
    }
  }, [file, url])

  if (loading) {
    return (
      <div className={`flex items-center justify-center ${className} bg-[#0A1525] border border-[#1E2A45]`}>
        <div className="flex flex-col items-center">
          <div className="h-12 w-12 rounded-none border-4 border-t-[#5FE496] border-[#1E2A45] animate-spin"></div>
          <p className="mt-4 text-white/70 font-['Avenir']">Loading model...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className={`flex items-center justify-center ${className} bg-[#0A1525] border border-[#1E2A45]`}>
        <div className="flex flex-col items-center text-center max-w-md px-4">
          <div className="h-12 w-12 rounded-none bg-[#0C1F3D] border border-[#1E2A45] flex items-center justify-center text-[#F46036]">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="24"
              height="24"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="square"
              strokeLinejoin="miter"
            >
              <path d="M12 9v4"></path>
              <path d="M12 17h.01"></path>
              <path d="M3 12a9 9 0 1 0 18 0 9 9 0 0 0-18 0z"></path>
            </svg>
          </div>
          <p className="mt-4 text-[#F46036] font-['Avenir']">{error}</p>
        </div>
      </div>
    )
  }

  if (!geometry && !file && !url) {
    return (
      <div className={`flex items-center justify-center ${className} bg-[#0A1525] border border-[#1E2A45]`}>
        <p className="text-white/50 font-['Avenir']">Upload a model to view it here</p>
      </div>
    )
  }

  return (
    <div className={className}>
      <Canvas camera={{ position: [0, 0, 5], fov: 50 }} gl={{ antialias: true }} shadows>
        <color attach="background" args={["#0A1525"]} />
        <ambientLight intensity={0.5} />
        <spotLight position={[10, 10, 10]} angle={0.15} penumbra={1} intensity={1} castShadow />
        <directionalLight position={[-5, 5, -5]} intensity={0.5} />

        {geometry && (
          <mesh castShadow receiveShadow scale={normalizedScale}>
            <primitive object={geometry} attach="geometry" />
            <meshStandardMaterial color="#CCCCCC" roughness={0.5} metalness={0.6} envMapIntensity={1} />
          </mesh>
        )}

        {showGrid && <gridHelper args={[10, 20, "#1E2A45", "#1E2A45"]} />}

        <OrbitControls
          autoRotate={autoRotate}
          autoRotateSpeed={1}
          enableZoom={interactive}
          enablePan={interactive}
          enableRotate={interactive}
          minDistance={2}
          maxDistance={10}
        />
        <Environment preset="studio" />
      </Canvas>
      
      {interactive && (
        <div className="absolute bottom-4 right-4 text-xs text-gray-400">
          Use mouse to rotate and zoom
        </div>
      )}
    </div>
  )
}

