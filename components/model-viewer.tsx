"use client"

import { useEffect, useState, useRef } from "react"
import { Canvas } from "@react-three/fiber"
import { OrbitControls, Environment, useGLTF } from "@react-three/drei"
import { STLLoader } from "three/examples/jsm/loaders/STLLoader.js"
import * as THREE from "three"
// Remove direct import of OCCT to prevent initialization errors
// import type { OCCTWorkerManager, ImportSettings, ImportResult } from "occt-import-js"

interface ModelViewerProps {
  file?: File
  url?: string
  autoRotate?: boolean
  interactive?: boolean
  showGrid?: boolean
  className?: string
}

// Function to handle centering and scaling, extracted for reuse
const centerAndScaleGeometry = (
  geometry: THREE.BufferGeometry | THREE.Group,
): { geometry: THREE.BufferGeometry | THREE.Group; scale: number } => {
  const box = new THREE.Box3().setFromObject(
    geometry instanceof THREE.BufferGeometry ? new THREE.Mesh(geometry) : geometry,
  )
  const center = new THREE.Vector3()
  box.getCenter(center)

  // For Groups (like GLTF scenes), we center by adjusting the group's position
  if (geometry instanceof THREE.Group) {
    geometry.position.sub(center)
  } else {
    // For BufferGeometry, we translate the vertices
    geometry.translate(-center.x, -center.y, -center.z)
  }

  const size = new THREE.Vector3()
  box.getSize(size)
  const maxDim = Math.max(size.x, size.y, size.z)

  const targetSize = 2 // Consistent target size
  const scale = maxDim === 0 ? 1 : targetSize / maxDim // Avoid division by zero

  return { geometry, scale }
}

// Component to load and display GLTF model (we'll only use this if OCCT is loaded)
function OcctGltfModel({
  gltfUrl,
  onLoaded,
}: {
  gltfUrl: string
  onLoaded: (scale: number) => void
}) {
  const { scene } = useGLTF(gltfUrl)

  useEffect(() => {
    if (scene) {
      // Apply centering and scaling when the GLTF scene is loaded
      const { scale } = centerAndScaleGeometry(scene)
      onLoaded(scale) // Pass the calculated scale back up
    }
    // Clean up the GLTF URL blob when the component unmounts or url changes
    return () => {
      if (gltfUrl.startsWith("blob:")) {
        URL.revokeObjectURL(gltfUrl)
      }
    }
  }, [scene, gltfUrl, onLoaded])

  // useGLTF handles loading state internally, just return the scene
  return scene ? <primitive object={scene} /> : null
}

export function ModelViewer({
  file,
  url,
  autoRotate = true,
  interactive = true,
  showGrid = false,
  className = "w-full h-full",
}: ModelViewerProps) {
  const [modelObject, setModelObject] = useState<
    THREE.BufferGeometry | string | null
  >(null)
  const [modelScale, setModelScale] = useState<number>(1)
  const [loading, setLoading] = useState<boolean>(true)
  const [error, setError] = useState<string | null>(null)
  
  // Effect to handle file/URL changes and load the model
  useEffect(() => {
    // Reset state when file/url becomes null
    if (!file && !url) {
      setLoading(false)
      setModelObject(null)
      setError(null)
      return
    }

    // Reset state for new file/url
    setLoading(true)
    setError(null)
    setModelObject(null)
    setModelScale(1) // Reset scale

    const fileUrl = file ? URL.createObjectURL(file) : url
    const fileName = file ? file.name : url?.substring(url.lastIndexOf("/") + 1)
    const fileType = fileName?.split(".").pop()?.toLowerCase()

    const loadFile = async () => {
      try {
        if (fileType === "stl") {
          // For STL files, proceed normally with STLLoader
          const loader = new STLLoader()
          loader.load(
            fileUrl as string,
            (geometry: THREE.BufferGeometry) => {
              try {
                geometry.computeVertexNormals() // Ensure normals are computed for STL
                const { scale } = centerAndScaleGeometry(geometry)
                setModelScale(scale)
                setModelObject(geometry)
                setLoading(false)
                console.log("[ModelViewer] STL loaded successfully:", fileName)
              } catch (err) {
                console.error("[ModelViewer] Error processing STL geometry:", err)
                setError("Failed to process the STL model.")
                setLoading(false)
              }
            },
            undefined, // Progress callback (optional)
            (err: any) => {
              console.error("[ModelViewer] Error loading STL:", err)
              setError(
                `Failed to load the STL model: ${err.message || "Unknown error"}`,
              )
              setLoading(false)
            },
          )
        } else if (fileType === "step" || fileType === "stp") {
          // For STEP/STP files, we need the OCCT library
          // Show a message since STEP loading is not currently working
          setError(
            "STEP/STP file viewing is temporarily unavailable. Please use STL files instead.",
          )
          setLoading(false)
          if (fileUrl?.startsWith("blob:")) URL.revokeObjectURL(fileUrl)
        } else {
          console.warn(`[ModelViewer] Unsupported file type: ${fileType}`)
          setError(
            `Unsupported file format: .${fileType}. Please upload STL files only for now.`,
          )
          setLoading(false)
        }
      } catch (err) {
        console.error("[ModelViewer] Exception during file loading:", err)
        setError(
          `An unexpected error occurred: ${err instanceof Error ? err.message : "Unknown error"}`,
        )
        setLoading(false)
      }
    }

    // Trigger the load
    loadFile()

    // Cleanup function for the effect
    return () => {
      // Revoke object URLs created for the file
      if (fileUrl && fileUrl.startsWith("blob:")) {
        console.log(`[ModelViewer] Revoking file object URL: ${fileUrl}`)
        URL.revokeObjectURL(fileUrl)
      }
    }
  }, [file, url]) // Remove OCCT dependencies

  // Callback for when the GLTF model is loaded
  const handleGltfLoaded = (scale: number) => {
    console.log(`[ModelViewer] GLTF Loaded, applying scale: ${scale}`)
    setModelScale(scale)
    setLoading(false) // Set loading false here for GLTF
  }

  // --- Render logic (mostly unchanged) ---
  if (loading && !modelObject) {
    // Show loading only if no model is ready yet
    return (
      <div
        className={`flex items-center justify-center ${className} bg-[#0A1525] border border-[#1E2A45]`}
      >
        <div className="flex flex-col items-center">
          <div className="h-12 w-12 rounded-none border-4 border-t-[#5FE496] border-[#1E2A45] animate-spin"></div>
          <p className="mt-4 text-white/70 font-['Avenir']">Loading model...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div
        className={`flex items-center justify-center ${className} bg-[#0A1525] border border-[#1E2A45]`}
      >
        <div className="flex flex-col items-center text-center max-w-xs px-4">
          {/* Error Icon SVG */}
          <div className="h-12 w-12 rounded-none bg-[#0C1F3D] border border-[#1E2A45] flex items-center justify-center text-[#F46036] mb-3">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="24"
              height="24"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <circle cx="12" cy="12" r="10"></circle>
              <line x1="12" y1="8" x2="12" y2="12"></line>
              <line x1="12" y1="16" x2="12.01" y2="16"></line>
            </svg>
          </div>
          <p className="text-[#F46036] font-['Avenir'] text-sm">{error}</p>
        </div>
      </div>
    )
  }

  if (!modelObject && !file && !url && !loading) {
    // Show placeholder only if not loading and no file/url
    return (
      <div
        className={`flex items-center justify-center ${className} bg-[#0A1525] border border-[#1E2A45]`}
      >
        <p className="text-white/50 font-['Avenir']">
          Upload a model to view it here
        </p>
      </div>
    )
  }

  // Only render Canvas if there's a model object or URL to load
  return (
    <div className={className}>
      <Canvas
        camera={{ position: [0, 0, 5], fov: 50 }}
        gl={{ antialias: true }}
        shadows
      >
        <color attach="background" args={["#0A1525"]} />
        <ambientLight intensity={1.0} />
        <directionalLight
          position={[5, 10, 7.5]}
          intensity={1.5}
          castShadow
          shadow-mapSize-width={1024}
          shadow-mapSize-height={1024}
        />
        <directionalLight position={[-5, -5, -5]} intensity={0.5} />
        <hemisphereLight groundColor={"#0A1525"} intensity={0.5} />

        {/* Render STL model */}
        {modelObject instanceof THREE.BufferGeometry && (
          <mesh castShadow receiveShadow scale={modelScale}>
            <primitive object={modelObject} attach="geometry" />
            <meshStandardMaterial
              color="#CCCCCC"
              roughness={0.5}
              metalness={0.1}
            />
          </mesh>
        )}

        {/* Render GLTF model (from STEP conversion) */}
        {typeof modelObject === "string" && modelObject.startsWith("blob:") && (
          <group scale={modelScale}>
            <OcctGltfModel
              gltfUrl={modelObject}
              onLoaded={handleGltfLoaded}
            />
          </group>
        )}

        {showGrid && <gridHelper args={[10, 20, "#1E2A45", "#1E2A45"]} />}

        <OrbitControls
          autoRotate={autoRotate}
          autoRotateSpeed={1}
          enableZoom={interactive}
          enablePan={interactive}
          enableRotate={interactive}
          minDistance={1}
          maxDistance={15}
        />
        <Environment preset="city" />
      </Canvas>

      {interactive && (
        <div className="absolute bottom-4 right-4 text-xs text-gray-400 bg-[#0A1525]/50 px-2 py-1 rounded">
          Use mouse to interact
        </div>
      )}
    </div>
  )
}

