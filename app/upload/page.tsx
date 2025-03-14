"use client"

import { useState, useCallback } from "react"
import { useDropzone } from "react-dropzone"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Upload, X, Check } from "lucide-react"
import { Canvas } from "@react-three/fiber"
import { OrbitControls, useGLTF, Environment } from "@react-three/drei"

function Model({ url }) {
  const { scene } = useGLTF(url)
  return <primitive object={scene} />
}

export default function UploadPage() {
  const [file, setFile] = useState(null)
  const [fileUrl, setFileUrl] = useState(null)
  const [isUploading, setIsUploading] = useState(false)
  const [uploadComplete, setUploadComplete] = useState(false)
  const [activeTab, setActiveTab] = useState("upload")

  const onDrop = useCallback((acceptedFiles) => {
    if (acceptedFiles?.length) {
      const file = acceptedFiles[0]
      setFile(file)
      setFileUrl(URL.createObjectURL(file))
      setIsUploading(true)

      // Simulate upload process
      setTimeout(() => {
        setIsUploading(false)
        setUploadComplete(true)
        setActiveTab("preview")
      }, 1500)
    }
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "model/gltf-binary": [".glb"],
      "model/gltf+json": [".gltf"],
    },
    maxFiles: 1,
  })

  const resetUpload = () => {
    setFile(null)
    setFileUrl(null)
    setUploadComplete(false)
    setActiveTab("upload")
  }

  return (
    <div className="container px-4 md:px-6 py-12">
      <div className="max-w-4xl mx-auto">
        <div className="space-y-4 mb-8">
          <h1 className="text-3xl font-bold tracking-tight">Upload your model</h1>
          <p className="text-lg text-white/70">
            Upload your 3D model to get an instant quote. We support .GLB and .GLTF files.
          </p>
        </div>

        <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
          <TabsList className="grid grid-cols-3 bg-oxford-blue border border-white/10">
            <TabsTrigger value="upload" disabled={isUploading}>
              Upload
            </TabsTrigger>
            <TabsTrigger value="preview" disabled={!fileUrl}>
              Preview
            </TabsTrigger>
            <TabsTrigger value="options" disabled={!fileUrl}>
              Options
            </TabsTrigger>
          </TabsList>

          <TabsContent value="upload" className="space-y-6">
            <Card className="border-white/10 bg-white/5">
              <CardContent className="p-0">
                <div
                  {...getRootProps()}
                  className={`
                    flex flex-col items-center justify-center p-12 border-2 border-dashed rounded-lg cursor-pointer
                    ${isDragActive ? "border-bleu-de-france bg-bleu-de-france/5" : "border-white/20 hover:border-white/30"}
                    ${file ? "bg-white/5" : ""}
                  `}
                >
                  <input {...getInputProps()} />

                  {isUploading ? (
                    <div className="flex flex-col items-center space-y-4">
                      <div className="h-12 w-12 rounded-full border-4 border-t-bleu-de-france border-white/20 animate-spin"></div>
                      <p className="text-lg font-medium">Uploading {file.name}...</p>
                    </div>
                  ) : file ? (
                    <div className="flex flex-col items-center space-y-4">
                      <div className="h-16 w-16 rounded-full bg-light-green/10 flex items-center justify-center">
                        <Check className="h-8 w-8 text-light-green" />
                      </div>
                      <div className="text-center">
                        <p className="text-lg font-medium">{file.name}</p>
                        <p className="text-sm text-white/50">{(file.size / (1024 * 1024)).toFixed(2)} MB</p>
                      </div>
                      <Button
                        variant="outline"
                        size="sm"
                        className="mt-4 border-white/10 hover:bg-white/5"
                        onClick={(e) => {
                          e.stopPropagation()
                          resetUpload()
                        }}
                      >
                        <X className="h-4 w-4 mr-2" />
                        Remove
                      </Button>
                    </div>
                  ) : (
                    <div className="flex flex-col items-center space-y-4 text-center">
                      <div className="h-16 w-16 rounded-full bg-bleu-de-france/10 flex items-center justify-center">
                        <Upload className="h-8 w-8 text-bleu-de-france" />
                      </div>
                      <div>
                        <p className="text-lg font-medium">Drag and drop your 3D model here</p>
                        <p className="text-sm text-white/50 mt-1">Or click to browse files</p>
                      </div>
                      <p className="text-xs text-white/50">Supports .GLB and .GLTF files up to 50MB</p>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>

            {file && uploadComplete && (
              <div className="flex justify-end">
                <Button
                  onClick={() => setActiveTab("preview")}
                  className="bg-bleu-de-france hover:bg-bleu-de-france/90"
                >
                  Continue to Preview
                </Button>
              </div>
            )}
          </TabsContent>

          <TabsContent value="preview" className="space-y-6">
            <Card className="border-white/10 bg-white/5">
              <CardContent className="p-0">
                {fileUrl && (
                  <div className="h-[500px] w-full">
                    <Canvas camera={{ position: [0, 0, 5], fov: 50 }}>
                      <ambientLight intensity={0.5} />
                      <spotLight position={[10, 10, 10]} angle={0.15} penumbra={1} />
                      <Model url={fileUrl} />
                      <OrbitControls />
                      <Environment preset="studio" />
                    </Canvas>
                  </div>
                )}
              </CardContent>
            </Card>

            <div className="flex justify-between">
              <Button
                variant="outline"
                onClick={() => setActiveTab("upload")}
                className="border-white/10 hover:bg-white/5"
              >
                Back to Upload
              </Button>
              <Button onClick={() => setActiveTab("options")} className="bg-bleu-de-france hover:bg-bleu-de-france/90">
                Continue to Options
              </Button>
            </div>
          </TabsContent>

          <TabsContent value="options" className="space-y-6">
            <Card className="border-white/10 bg-white/5">
              <CardContent className="p-6">
                <div className="space-y-6">
                  <div>
                    <h3 className="text-lg font-medium mb-2">Manufacturing Options</h3>
                    <p className="text-sm text-white/70 mb-4">
                      Select your preferred manufacturing process and material.
                    </p>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div className="p-4 rounded-lg border border-white/10 bg-white/5 hover:bg-white/10 cursor-pointer transition-colors">
                        <h4 className="font-medium">3D Printing</h4>
                        <p className="text-sm text-white/50 mt-1">Fast turnaround, good for prototypes</p>
                      </div>
                      <div className="p-4 rounded-lg border border-white/10 bg-white/5 hover:bg-white/10 cursor-pointer transition-colors">
                        <h4 className="font-medium">CNC Machining</h4>
                        <p className="text-sm text-white/50 mt-1">High precision, excellent finish</p>
                      </div>
                      <div className="p-4 rounded-lg border border-white/10 bg-white/5 hover:bg-white/10 cursor-pointer transition-colors">
                        <h4 className="font-medium">Injection Molding</h4>
                        <p className="text-sm text-white/50 mt-1">Best for high volume production</p>
                      </div>
                      <div className="p-4 rounded-lg border border-white/10 bg-white/5 hover:bg-white/10 cursor-pointer transition-colors">
                        <h4 className="font-medium">Sheet Metal</h4>
                        <p className="text-sm text-white/50 mt-1">Ideal for enclosures and brackets</p>
                      </div>
                    </div>
                  </div>

                  <div>
                    <h3 className="text-lg font-medium mb-2">Quantity</h3>
                    <div className="flex items-center space-x-4">
                      <Button variant="outline" className="border-white/10 hover:bg-white/5 w-16">
                        1
                      </Button>
                      <Button variant="outline" className="border-white/10 hover:bg-white/5 w-16">
                        5
                      </Button>
                      <Button variant="outline" className="border-white/10 hover:bg-white/5 w-16">
                        10
                      </Button>
                      <Button variant="outline" className="border-white/10 hover:bg-white/5 w-16">
                        25
                      </Button>
                      <Button variant="outline" className="border-white/10 hover:bg-white/5 w-16">
                        50+
                      </Button>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>

            <div className="flex justify-between">
              <Button
                variant="outline"
                onClick={() => setActiveTab("preview")}
                className="border-white/10 hover:bg-white/5"
              >
                Back to Preview
              </Button>
              <Button className="bg-bleu-de-france hover:bg-bleu-de-france/90">Get Quote</Button>
            </div>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  )
}

