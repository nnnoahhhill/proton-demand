"use client";

import { useState, useRef, FormEvent, ChangeEvent } from "react";
import { getQuote, materialOptions, finishOptions, QuoteResponse, DFMIssue } from "@/lib/api";
import { GlowButton } from "@/components/ui/glow-button";
import { useCart } from "@/lib/cart";
import { useRouter } from "next/navigation";
import { ModelViewer } from "@/components/model-viewer";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { FileUp, Info, RotateCw, Eye, EyeOff } from "lucide-react";

// Define the process type for stricter typing
type ProcessType = 'CNC' | '3DP_SLA' | '3DP_SLS' | '3DP_FDM' | 'SHEET_METAL';

// Define option type
interface Option {
  value: string;
  label: string;
}

const processOptions: Option[] = [
  { value: 'CNC', label: 'CNC Machining' },
  { value: '3DP_SLA', label: '3D Printing (SLA)' },
  { value: '3DP_SLS', label: '3D Printing (SLS)' },
  { value: '3DP_FDM', label: '3D Printing (FDM)' },
  { value: 'SHEET_METAL', label: 'Sheet Metal' },
];

export default function NewQuoteForm() {
  const [process, setProcess] = useState<ProcessType>('3DP_FDM');
  const [material, setMaterial] = useState<string>('');
  const [finish, setFinish] = useState<string>('');
  const [modelFile, setModelFile] = useState<File | null>(null);
  const [drawingFile, setDrawingFile] = useState<File | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [response, setResponse] = useState<QuoteResponse | null>(null);
  const [error, setError] = useState<string>('');
  const [addedToCart, setAddedToCart] = useState(false);
  const [dragActive, setDragActive] = useState(false);
  const [showModelControls, setShowModelControls] = useState(true);

  // Get cart context
  const { addItem } = useCart();
  const router = useRouter();

  // Refs for the file inputs
  const modelFileRef = useRef<HTMLInputElement>(null);
  const drawingFileRef = useRef<HTMLInputElement>(null);

  // Handle process change
  const handleProcessChange = (value: string) => {
    const newProcess = value as ProcessType;
    setProcess(newProcess);
    // Reset material and finish when process changes
    setMaterial('');
    setFinish('');
  };

  // Handle model file selection
  const handleModelFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const file = e.target.files[0];
      console.log("Model file selected:", file.name, "Size:", file.size, "bytes");

      if (file.size === 0) {
        setError('The selected model file is empty. Please select a valid file.');
        setModelFile(null);
        return;
      }

      // Check file extension
      const fileExtension = file.name.split('.').pop()?.toLowerCase();
      if (!fileExtension || !['stl', 'step', 'stp'].includes(fileExtension)) {
        setError('Please upload a valid .stl or .step file.');
        setModelFile(null);
        return;
      }

      setModelFile(file);
      setError(''); // Clear any previous errors
    }
  };

  // Handle drawing file selection
  const handleDrawingFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const file = e.target.files[0];
      console.log("Drawing file selected:", file.name, "Size:", file.size, "bytes");

      if (file.size === 0) {
        setError('The selected drawing file is empty. Please select a valid file.');
        setDrawingFile(null);
        return;
      }

      // Check file extension
      const fileExtension = file.name.split('.').pop()?.toLowerCase();
      if (!fileExtension || !['pdf'].includes(fileExtension)) {
        setError('Please upload a valid PDF file for engineering drawings.');
        setDrawingFile(null);
        return;
      }

      setDrawingFile(file);
      setError(''); // Clear any previous errors related to file
    }
  };

  // Handle drag and drop
  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const file = e.dataTransfer.files[0];
      const fileExtension = file.name.split('.').pop()?.toLowerCase();

      if (fileExtension && ['stl', 'step', 'stp'].includes(fileExtension)) {
        setModelFile(file);
        setError(''); // Clear any previous errors
      } else {
        setError('Please upload a valid .stl or .step file.');
      }
    }
  };

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(true);
  };

  const handleDragEnter = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(true);
  };

  const handleDragLeave = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
  };

  // Handle form submission
  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();

    // Validate form
    if (!process) {
      setError('Please select a manufacturing process');
      return;
    }

    if (!material) {
      setError('Please select a material');
      return;
    }

    if (!finish) {
      setError('Please select a finish');
      return;
    }

    if (!modelFile) {
      setError('Please upload a 3D model file');
      return;
    }

    console.log("Submitting form with:",
      "process=", process,
      "material=", material,
      "finish=", finish,
      "modelFile=", modelFile.name,
      "drawingFile=", drawingFile ? drawingFile.name : "none"
    );

    // Clear previous results
    setError('');
    setResponse(null);
    setLoading(true);
    setAddedToCart(false);

    try {
      // Get quote from API
      const quoteResponse = await getQuote({
        process,
        material,
        finish,
        modelFile,
        drawingFile: drawingFile || undefined
      });

      console.log("API response:", quoteResponse);

      // Set response
      setResponse(quoteResponse);

      // Check for errors
      if (!quoteResponse.success) {
        console.error("API error:", quoteResponse.error || quoteResponse.message);
        setError(quoteResponse.error || quoteResponse.message || 'Failed to get quote');
      }
    } catch (err) {
      console.error('Error submitting quote form:', err);
      setError(err instanceof Error ? err.message : 'An unknown error occurred');
    } finally {
      setLoading(false);
    }
  };

  // Add to cart
  const handleAddToCart = () => {
    if (response && response.success && modelFile) {
      addItem(response, modelFile.name);
      setAddedToCart(true);
    }
  };

  // Proceed to checkout
  const handleCheckout = () => {
    if (response && response.success && modelFile) {
      if (!addedToCart) {
        addItem(response, modelFile.name);
      }
      router.push('/checkout');
    }
  };

  // Reset the form
  const handleReset = () => {
    setProcess('CNC');
    setMaterial('');
    setFinish('');
    setModelFile(null);
    setDrawingFile(null);
    setResponse(null);
    setError('');
    setAddedToCart(false);

    // Reset file inputs
    if (modelFileRef.current) modelFileRef.current.value = '';
    if (drawingFileRef.current) drawingFileRef.current.value = '';
  };

  return (
    <div className="grid gap-6 md:grid-cols-2">
      {/* Left Column - Model Upload */}
      <div>
        <div className="border border-[#1E2A45] bg-[#0C1F3D]/50 p-4 mb-4">
          <h2 className="text-xl font-andale mb-4 text-white">Upload Your 3D Model</h2>
          <p className="text-white/70 mb-4 font-avenir">
            Upload your STL or STEP file for 3D printing
          </p>

          <div className="space-y-4">
            <div className="space-y-2">
              <label className="block text-sm font-medium text-white font-avenir">Upload 3D Model</label>
              <div className="flex items-center justify-center w-full">
                {modelFile ? (
                  <div className="w-full">
                    <div className="relative">
                      <ModelViewer
                        file={modelFile}
                        autoRotate={!showModelControls}
                        interactive={showModelControls}
                        className="h-[250px] w-full"
                      />
                      <button
                        onClick={() => setShowModelControls(!showModelControls)}
                        className="absolute top-2 right-2 bg-[#0A1525]/70 hover:bg-[#0A1525]/90 border border-[#1E2A45] p-1 rounded-none"
                      >
                        {showModelControls ? (
                          <EyeOff className="h-4 w-4 text-white" />
                        ) : (
                          <Eye className="h-4 w-4 text-white" />
                        )}
                      </button>
                    </div>
                    <div className="mt-2 flex justify-between items-center">
                      <p className="text-sm font-medium text-white font-avenir">{modelFile.name}</p>
                      <button
                        onClick={() => {
                          setModelFile(null);
                          if (modelFileRef.current) modelFileRef.current.value = '';
                        }}
                        className="flex items-center gap-1 text-sm text-white bg-[#0C1F3D] hover:bg-[#0C1F3D]/80 border border-[#1E2A45] px-2 py-1 rounded-none"
                      >
                        <RotateCw className="h-3 w-3" />
                        Change File
                      </button>
                    </div>
                  </div>
                ) : (
                  <div
                    className={`flex flex-col items-center justify-center w-full h-[250px] border-2 border-dashed rounded-none cursor-pointer ${
                      dragActive ? "bg-[#0C1F3D]/80 border-[#5fe496]" : "bg-[#0C1F3D]/40 hover:bg-[#0C1F3D]/60 border-[#1E2A45]"
                    }`}
                    onDrop={handleDrop}
                    onDragOver={handleDragOver}
                    onDragEnter={handleDragEnter}
                    onDragLeave={handleDragLeave}
                    onClick={() => modelFileRef.current?.click()}
                  >
                    <div className="flex flex-col items-center justify-center pt-5 pb-6">
                      <FileUp className="w-8 h-8 mb-2 text-white/50" />
                      <p className="mb-2 text-sm text-white/70 font-avenir">
                        <span className="font-semibold">Click to upload</span> or drag and drop
                      </p>
                      <p className="text-xs text-white/50 font-avenir">STL or STEP files (Max. 50MB)</p>
                    </div>
                    <input
                      ref={modelFileRef}
                      type="file"
                      accept=".stl,.step,.stp"
                      className="hidden"
                      onChange={handleModelFileChange}
                    />
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Right Column - Manufacturing Options */}
      <div>
        <div className="border border-[#1E2A45] bg-[#0C1F3D]/50 p-4 mb-4">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-andale text-white">Manufacturing Options</h2>

            <div className="flex space-x-2">
              <div className="relative group">
                <button className="text-[#5fe496] border border-[#1E2A45] bg-[#0A1525] px-3 py-1 text-sm rounded-none">
                  3D Printing
                </button>
              </div>

              <div className="relative group">
                <button className="text-white/50 border border-[#1E2A45] bg-[#0A1525] px-3 py-1 text-sm rounded-none opacity-50 cursor-not-allowed">
                  CNC
                </button>
                <div className="absolute bottom-full mb-2 right-0 hidden group-hover:block bg-[#0C1F3D] border border-[#1E2A45] p-2 rounded-none text-xs text-white/70 w-32 z-10 text-center">
                  Coming Soon!
                </div>
              </div>

              <div className="relative group">
                <button className="text-white/50 border border-[#1E2A45] bg-[#0A1525] px-3 py-1 text-sm rounded-none opacity-50 cursor-not-allowed">
                  Sheet Metal
                </button>
                <div className="absolute bottom-full mb-2 right-0 hidden group-hover:block bg-[#0C1F3D] border border-[#1E2A45] p-2 rounded-none text-xs text-white/70 w-32 z-10 text-center">
                  Coming Soon!
                </div>
              </div>
            </div>
          </div>

          <div className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <label className="block text-sm font-medium text-white font-avenir">Material</label>
                <select
                  value={material}
                  onChange={(e) => setMaterial(e.target.value)}
                  className="w-full bg-[#0A1525] border border-[#1E2A45] text-white p-2 rounded-none focus:outline-none focus:ring-1 focus:ring-[#5fe496] font-avenir"
                >
                  <option value="" disabled>Select material</option>
                  {materialOptions[process]?.map((option: Option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </div>

              <div className="space-y-2">
                <label className="block text-sm font-medium text-white font-avenir">Quantity</label>
                <input
                  type="number"
                  min="1"
                  defaultValue="1"
                  className="w-full bg-[#0A1525] border border-[#1E2A45] text-white p-2 rounded-none focus:outline-none focus:ring-1 focus:ring-[#5fe496] font-avenir"
                />
              </div>
            </div>

              {(process === '3DP_FDM' || process === '3DP_SLA' || process === '3DP_SLS') && (
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <label className="block text-sm font-medium text-white font-avenir">Finish</label>
                    <div className="relative group">
                      <Info className="h-4 w-4 text-white/50" />
                      <div className="absolute bottom-full mb-2 left-1/2 transform -translate-x-1/2 hidden group-hover:block bg-[#0C1F3D] border border-[#1E2A45] p-2 rounded-none text-xs text-white/70 w-48 z-10">
                        Different finishes can improve the appearance and durability of your printed parts.
                      </div>
                    </div>
                  </div>

                  <select
                    value={finish}
                    onChange={(e) => setFinish(e.target.value)}
                    className="w-full bg-[#0A1525] border border-[#1E2A45] text-white p-2 rounded-none focus:outline-none focus:ring-1 focus:ring-[#5fe496] font-avenir"
                  >
                    <option value="" disabled>Select finish</option>
                    {finishOptions[process]?.map((option: Option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </div>
              )}

              {process === 'CNC' && (
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <label className="block text-sm font-medium text-white font-avenir">Surface Finish</label>
                    <div className="relative group">
                      <Info className="h-4 w-4 text-white/50" />
                      <div className="absolute bottom-full mb-2 left-1/2 transform -translate-x-1/2 hidden group-hover:block bg-[#0C1F3D] border border-[#1E2A45] p-2 rounded-none text-xs text-white/70 w-48 z-10">
                        Surface finish affects both the appearance and functionality of your parts.
                      </div>
                    </div>
                  </div>

                  <select
                    value={finish}
                    onChange={(e) => setFinish(e.target.value)}
                    className="w-full bg-[#0A1525] border border-[#1E2A45] text-white p-2 rounded-none focus:outline-none focus:ring-1 focus:ring-[#5fe496] font-avenir"
                  >
                    <option value="" disabled>Select finish</option>
                    {finishOptions[process]?.map((option: Option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </div>
              )}

              {process === 'SHEET_METAL' && (
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <label className="block text-sm font-medium text-white font-avenir">Finishing Options</label>
                    <div className="relative group">
                      <Info className="h-4 w-4 text-white/50" />
                      <div className="absolute bottom-full mb-2 left-1/2 transform -translate-x-1/2 hidden group-hover:block bg-[#0C1F3D] border border-[#1E2A45] p-2 rounded-none text-xs text-white/70 w-48 z-10">
                        Finishing options can improve corrosion resistance and appearance.
                      </div>
                    </div>
                  </div>

                  <select
                    value={finish}
                    onChange={(e) => setFinish(e.target.value)}
                    className="w-full bg-[#0A1525] border border-[#1E2A45] text-white p-2 rounded-none focus:outline-none focus:ring-1 focus:ring-[#5fe496] font-avenir"
                  >
                    <option value="" disabled>Select finish</option>
                    {finishOptions[process]?.map((option: Option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </div>
              )}

              {(process === '3DP_FDM' || process === '3DP_SLA' || process === '3DP_SLS') && (
                <div className="space-y-2">
                  <label className="block text-sm font-medium text-white font-avenir">Lead Time</label>
                  <select className="w-full bg-[#0A1525] border border-[#1E2A45] text-white p-2 rounded-none focus:outline-none focus:ring-1 focus:ring-[#5fe496] font-avenir">
                    <option value="standard" selected>Standard (7-10 days)</option>
                    <option value="expedited">Expedited (5-7 days)</option>
                    <option value="rush">Rush (3-5 days)</option>
                  </select>
                </div>
              )}

              <div className="space-y-2">
                <label htmlFor="notes" className="block text-sm font-medium text-white font-avenir">Special Instructions</label>
                <textarea
                  id="notes"
                  className="w-full bg-[#0A1525] border border-[#1E2A45] text-white p-2 rounded-none focus:outline-none focus:ring-1 focus:ring-[#5fe496] min-h-[60px] font-avenir"
                  placeholder="Add any special requirements..."
                />
              </div>

              <div className="mt-4">
                <GlowButton onClick={handleSubmit} className="w-full" disabled={loading}>
                  {loading ? 'Processing...' : 'Generate Quote'}
                </GlowButton>
              </div>
            </div>
          </div>
        </div>
      </div>
      <div className="space-y-6">
        {/* Error message */}
        {error && (
          <div className="p-4 border border-[#F46036] bg-[#F46036]/10 text-[#F46036] font-avenir">
            {error}
          </div>
        )}

        {/* Success message */}
        {response?.success && (
          <div className="p-4 border border-[#5fe496] bg-[#5fe496]/10 text-[#5fe496] font-avenir">
            <h3 className="text-xl font-andale mb-2">Quote Generated!</h3>
            <div className="space-y-2">
              <p><span className="font-medium">Quote ID:</span> {response.quoteId}</p>
              <p><span className="font-medium">Price:</span> ${response.price?.toFixed(2)} {response.currency}</p>
              <p><span className="font-medium">Lead Time:</span> {response.leadTimeInDays} days</p>

              <div className="mt-4 flex flex-wrap gap-4">
                <GlowButton onClick={handleReset}>New Quote</GlowButton>

                {addedToCart ? (
                  <GlowButton
                    onClick={handleCheckout}
                    className="bg-[#5fe496] text-[#0A1525] hover:bg-[#5fe496]/80"
                  >
                    Proceed to Checkout
                  </GlowButton>
                ) : (
                  <GlowButton
                    onClick={handleAddToCart}
                    className="bg-[#F46036] text-white hover:bg-[#F46036]/80"
                  >
                    Add to Cart
                  </GlowButton>
                )}

                {addedToCart && (
                  <GlowButton
                    onClick={handleCheckout}
                    className="bg-[#1e87d6] text-white hover:bg-[#1e87d6]/80"
                  >
                    View Cart
                  </GlowButton>
                )}
              </div>
            </div>
          </div>
        )}

        {/* DFM issues */}
        {response?.dfmIssues && response.dfmIssues.length > 0 && (
          <div className="p-4 border border-[#F46036] bg-[#F46036]/10 font-avenir">
            <h3 className="text-xl font-andale mb-2 text-[#F46036]">Manufacturing Issues</h3>
            <p className="mb-4">The part cannot be manufactured due to the following issues:</p>
            <ul className="list-disc pl-5 space-y-2">
              {response.dfmIssues.map((issue: DFMIssue, index: number) => (
                <li key={index} className="text-[#F46036]">
                  <span className="font-medium">{issue.type}: </span>
                  <span>{issue.description}</span>
                  {issue.location && (
                    <span className="block text-sm">
                      Location: x={issue.location.x.toFixed(2)}, y={issue.location.y.toFixed(2)}, z={issue.location.z.toFixed(2)}
                    </span>
                  )}
                </li>
              ))}
            </ul>

            <div className="mt-4">
              <GlowButton onClick={handleReset}>Try Again</GlowButton>
            </div>
          </div>
        )}

        {!response?.success && !response?.dfmIssues && (
          <>
            <div className="border border-[#1E2A45] bg-[#0C1F3D]/50 p-4">
              <h2 className="text-xl font-andale mb-4 text-white">Additional Options</h2>
              <p className="text-white/70 mb-4 font-avenir">Customize your manufacturing requirements</p>

              <div className="space-y-4">
}




          </>
        )}
      </div>
    </div>
  );
}
