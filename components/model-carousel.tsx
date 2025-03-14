"use client"

import { useState, useEffect } from "react"
import { Canvas } from "@react-three/fiber"
import { OrbitControls, Environment } from "@react-three/drei"
import * as THREE from "three"
import { STLLoader } from "three/examples/jsm/loaders/STLLoader.js"

// Define types for models and props
interface Model {
  id: number
  path: string
  position: [number, number, number]
  rotation: [number, number, number]
  scale: number
}

interface ModelProps {
  url: string
  position: [number, number, number]
  rotation: [number, number, number]
  scale: number
}

// Sample models
const models: Model[] = [
  {
    id: 1,
    path: "/test-models/3DP_CupHolder.stl",
    position: [0, 0, 0],
    rotation: [0, 0, 0],
    scale: 1.5,
  },
  {
    id: 2,
    path: "/test-models/CNC_Nozzle.stl",
    position: [0, 0, 0],
    rotation: [0, 0, 0],
    scale: 1,
  },
  {
    id: 3,
    path: "/test-models/SM_DrainGrate.stl",
    position: [0, 0, 0],
    rotation: [0, 0, 0],
    scale: 1,
  },
]

function Model({ url, position, rotation, scale }: ModelProps) {
  const [geometry, setGeometry] = useState<THREE.BufferGeometry | null>(null)
  const [normalizedScale, setNormalizedScale] = useState<number>(1)

  useEffect(() => {
    const loader = new STLLoader()

    try {
      loader.load(
        url,
        (geometry: THREE.BufferGeometry) => {
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
        },
        undefined,
        (error: any) => {
          console.error("Error loading STL:", error)
        },
      )
    } catch (error) {
      console.error("Error in STL loading process:", error)
    }
  }, [url])

  if (!geometry) {
    return null
  }

  // Apply the normalized scale multiplied by the model's intended scale factor
  const finalScale = normalizedScale * scale

  return (
    <group position={position} rotation={rotation} scale={finalScale}>
      <mesh castShadow receiveShadow>
        <primitive object={geometry} attach="geometry" />
        <meshStandardMaterial color="#CCCCCC" roughness={0.5} metalness={0.8} envMapIntensity={2} />
      </mesh>
    </group>
  )
}

export function ModelCarousel() {
  const [currentModelIndex, setCurrentModelIndex] = useState(0)

  // Auto-rotate through models every 8 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentModelIndex((prev) => (prev + 1) % models.length)
    }, 8000)

    return () => clearInterval(interval)
  }, [])

  const currentModel = models[currentModelIndex]

  return (
    <div className="h-[500px] w-full relative">
      <Canvas camera={{ position: [0, 0, 5], fov: 50 }} gl={{ antialias: true, alpha: true }} shadows>
        <ambientLight intensity={0.5} />
        <spotLight position={[10, 10, 10]} angle={0.15} penumbra={1} intensity={1} castShadow />
        <directionalLight position={[-5, 5, -5]} intensity={0.5} />

        <Model
          url={currentModel.path}
          position={currentModel.position}
          rotation={currentModel.rotation}
          scale={currentModel.scale}
        />

        <OrbitControls
          enablePan={true}
          enableZoom={true}
          autoRotate
          autoRotateSpeed={1.5}
          // Removed minPolarAngle and maxPolarAngle to allow full rotation
        />
        <Environment preset="studio" />
      </Canvas>

      <div className="absolute bottom-4 left-1/2 transform -translate-x-1/2 flex space-x-2">
        {models.map((_, index) => (
          <button
            key={index}
            className={`h-1.5 w-1.5 rounded-full transition-all duration-300 ${
              index === currentModelIndex ? "bg-[#5FE496] w-3" : "bg-[#1E2A45]"
            }`}
            onClick={() => setCurrentModelIndex(index)}
          />
        ))}
      </div>
      
      <div className="absolute bottom-4 right-4 text-xs text-gray-400">
        Use mouse to rotate and zoom
      </div>
    </div>
  )
}

