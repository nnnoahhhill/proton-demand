"use client"

import { useState, useCallback } from "react"
import { useDropzone } from "react-dropzone"
import { GlowButton } from "@/components/ui/glow-button"
import { Card, CardContent } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Upload, X, Check, Terminal, AlertTriangle } from "lucide-react"
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group"
import { Label } from "@/components/ui/label"
import { Input } from "@/components/ui/input"
import { ModelViewer } from "@/components/model-viewer"
import QuoteForm from './QuoteForm'

type ServiceType = "cnc" | "3d" | "sheet";

export default function QuotePage() {
  const [file, setFile] = useState<File | null>(null)
  const [isUploading, setIsUploading] = useState(false)
  const [uploadComplete, setUploadComplete] = useState(false)
  const [activeTab, setActiveTab] = useState("upload")
  const [selectedService, setSelectedService] = useState<ServiceType>("cnc")
  const [quantity, setQuantity] = useState(1)
  const [estimatedPrice, setEstimatedPrice] = useState<number | null>(null)

  const onDrop = useCallback(
    (acceptedFiles: File[]) => {
      if (acceptedFiles?.length) {
        const file = acceptedFiles[0]
        setFile(file)
        setIsUploading(true)

        // Simulate upload process
        setTimeout(() => {
          setIsUploading(false)
          setUploadComplete(true)
          setActiveTab("preview")

          // Simulate price estimation based on file size
          const basePrice = selectedService === "cnc" ? 30 : selectedService === "3d" ? 12 : 25
          const sizeMultiplier = (file.size / (1024 * 1024)) * 0.5 // $0.50 per MB
          setEstimatedPrice(Math.round((basePrice + sizeMultiplier) * quantity))
        }, 1500)
      }
    },
    [selectedService, quantity],
  )

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "model/step": [".step", ".stp"],
      "model/stl": [".stl"],
    },
    maxFiles: 1,
    maxSize: 50 * 1024 * 1024, // 50MB
  })

  const resetUpload = () => {
    setFile(null)
    setUploadComplete(false)
    setActiveTab("upload")
    setEstimatedPrice(null)
  }

  const handleServiceChange = (value: ServiceType) => {
    setSelectedService(value)
    if (file && uploadComplete) {
      // Recalculate price when service changes
      const basePrice = value === "cnc" ? 30 : value === "3d" ? 12 : 25
      const sizeMultiplier = (file.size / (1024 * 1024)) * 0.5
      setEstimatedPrice(Math.round((basePrice + sizeMultiplier) * quantity))
    }
  }

  const handleQuantityChange = (value: number) => {
    setQuantity(value)
    if (file && uploadComplete) {
      // Recalculate price when quantity changes
      const basePrice = selectedService === "cnc" ? 30 : selectedService === "3d" ? 12 : 25
      const sizeMultiplier = (file.size / (1024 * 1024)) * 0.5
      setEstimatedPrice(Math.round((basePrice + sizeMultiplier) * value))
    }
  }

  return (
    <div className="container px-4 md:px-6 py-12">
      <div className="max-w-4xl mx-auto">
        <div className="space-y-4 mb-8">
          <div className="inline-flex items-center rounded-none border border-[#1E2A45] bg-[#0A1525]/80 px-3 py-1 text-sm">
            <span className="text-[#5fe496] font-andale">QUOTE</span>
          </div>
          <h1 className="text-3xl font-andale tracking-tight">Get Instant Quote</h1>
          <p className="text-lg text-white/70 font-avenir">
            Upload your design and get a real-time quote with DFM analysis.
          </p>
        </div>
        
        <div className="grid grid-cols-1 gap-8">
          <QuoteForm />
          
          <div className="glow-card rounded-none border border-[#1E2A45] bg-[#0C1F3D]/30 p-8 backdrop-blur-sm">
            <h2 className="text-2xl font-andale mb-4">How it Works</h2>
            <div className="space-y-4">
              <div className="flex items-start">
                <div className="w-8 h-8 rounded-none bg-[#0A1525] border border-[#1E2A45] flex items-center justify-center mr-4 mt-1">
                  <span className="font-andale text-[#5fe496]">1</span>
                </div>
                <div>
                  <h3 className="text-lg font-andale mb-1">Upload Your Model</h3>
                  <p className="text-white/70 font-avenir">
                    Upload your 3D model file (STL or STEP) and optionally a drawing file (PDF).
                  </p>
                </div>
              </div>
              
              <div className="flex items-start">
                <div className="w-8 h-8 rounded-none bg-[#0A1525] border border-[#1E2A45] flex items-center justify-center mr-4 mt-1">
                  <span className="font-andale text-[#5fe496]">2</span>
                </div>
                <div>
                  <h3 className="text-lg font-andale mb-1">DFM Analysis</h3>
                  <p className="text-white/70 font-avenir">
                    Our system analyzes your design for manufacturability, identifying any issues that could affect production.
                  </p>
                </div>
              </div>
              
              <div className="flex items-start">
                <div className="w-8 h-8 rounded-none bg-[#0A1525] border border-[#1E2A45] flex items-center justify-center mr-4 mt-1">
                  <span className="font-andale text-[#5fe496]">3</span>
                </div>
                <div>
                  <h3 className="text-lg font-andale mb-1">Get Your Quote</h3>
                  <p className="text-white/70 font-avenir">
                    Receive an instant price quote and lead time estimate. No sales calls, no middlemen, no markup.
                  </p>
                </div>
              </div>
              
              <div className="flex items-start">
                <div className="w-8 h-8 rounded-none bg-[#0A1525] border border-[#1E2A45] flex items-center justify-center mr-4 mt-1">
                  <span className="font-andale text-[#5fe496]">4</span>
                </div>
                <div>
                  <h3 className="text-lg font-andale mb-1">Place Order</h3>
                  <p className="text-white/70 font-avenir">
                    When you're ready, place your order with a single click. We'll manufacture your parts and ship them directly to you.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

