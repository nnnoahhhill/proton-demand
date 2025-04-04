"use client";

import { useState, useRef, FormEvent, ChangeEvent, useEffect } from "react";
import { getQuote, materialOptions, finishOptions, QuoteResponse, DFMIssue } from "@/lib/api";
import { GlowButton } from "@/components/ui/glow-button";
import { useCart } from "@/lib/cart";
import { useRouter } from "next/navigation";
import { ModelViewer } from "@/components/model-viewer";
import { FileUp, Info, RotateCw, Eye, EyeOff } from "lucide-react";

// Define the process type for stricter typing
type ProcessType = '3DP_FDM' | '3DP_SLA' | '3DP_SLS' | 'CNC' | 'SHEET_METAL';

// Define option type
interface Option {
  value: string;
  label: string;
}

export default function NewQuoteForm() {
  const [process, setProcess] = useState<ProcessType>('3DP_FDM');
  const [material, setMaterial] = useState<string>('');
  const [finish, setFinish] = useState<string>('standard'); // Default to standard finish
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
  const handleProcessChange = (value: ProcessType) => {
    setProcess(value);
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

    if (!modelFile) {
      setError('Please upload a 3D model file');
      return;
    }

    // Set default finish based on process
    if (!finish) {
      if (process === '3DP_FDM') {
        setFinish('standard');
      } else if (process === '3DP_SLA') {
        setFinish('standard');
      } else if (process === '3DP_SLS') {
        setFinish('standard');
      }
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
      // Always use standard finish for 3D printing
      const standardFinish = 'standard';

      const quoteResponse = await getQuote({
        process,
        material,
        finish: standardFinish,
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

  // Auto-dismiss error message after 5 seconds
  useEffect(() => {
    if (error) {
      const timer = setTimeout(() => {
        setError('');
      }, 5000);

      return () => clearTimeout(timer);
    }
  }, [error]);

  // Reset the form
  const handleReset = () => {
    setProcess('3DP_FDM');
    setMaterial('');
    setFinish('standard'); // Keep standard finish
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
        <div className="border border-[#1E2A45] bg-[#0C1F3D]/50 p-4 mb-4 h-full flex flex-col">
          <h2 className="text-xl font-andale mb-4 text-white">Upload Your 3D Model</h2>
          <p className="text-white/70 mb-4 font-avenir">
            Upload your STL or STEP file for 3D printing
          </p>

          <div className="flex-grow flex flex-col">
            <div className="flex-grow">
              <label className="block text-sm font-medium text-white font-avenir mb-2">Upload 3D Model</label>
              <div className="flex items-center justify-center w-full h-[calc(100%-30px)]">
                {modelFile ? (
                  <div className="w-full h-full">
                    <div className="relative h-[300px]">
                      <ModelViewer
                        file={modelFile}
                        autoRotate={!showModelControls}
                        interactive={showModelControls}
                        className="h-full w-full"
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
                    className={`flex flex-col items-center justify-center w-full h-[300px] border-2 border-dashed rounded-none cursor-pointer ${
                      dragActive ? "bg-[#0C1F3D]/80 border-[#5fe496]" : "bg-[#0C1F3D]/40 hover:bg-[#0C1F3D]/60 border-[#1E2A45]"
                    }`}
                    onDrop={handleDrop}
                    onDragOver={handleDragOver}
                    onDragEnter={handleDragEnter}
                    onDragLeave={handleDragLeave}
                    onClick={() => modelFileRef.current?.click()}
                  >
                    <div className="flex flex-col items-center justify-center">
                      <FileUp className="w-12 h-12 mb-4 text-white/50" />
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
        {/* Error message - Toast style with auto-dismiss */}
        {error && (
          <div className="absolute top-1/4 left-1/2 transform -translate-x-1/2 z-50 p-4 border border-[#F46036] bg-[#0A1525] text-[#F46036] font-avenir shadow-lg max-w-md transition-opacity duration-300 ease-in-out opacity-90 hover:opacity-100">
            <div className="flex justify-between items-start">
              <div>{error}</div>
              <button
                onClick={() => setError('')}
                className="ml-4 text-white/70 hover:text-white"
              >
                ×
              </button>
            </div>
          </div>
        )}

        {/* Success message */}
        {response?.success && (
          <div className="border border-[#1E2A45] bg-[#0C1F3D]/50 p-4 h-full flex flex-col">
            <div className="mb-6 border border-[#5fe496] bg-[#5fe496]/10 p-4">
              <h3 className="text-xl font-andale mb-2 text-[#5fe496]">Quote Generated!</h3>
              <div className="space-y-2 text-white">
                <p><span className="font-medium">Quote ID:</span> {response.quoteId}</p>
                <p><span className="font-medium">Price:</span> ${response.price?.toFixed(2)} {response.currency}</p>
                <p><span className="font-medium">Lead Time:</span> {response.leadTimeInDays} days</p>
                <p><span className="font-medium">Process:</span> {process.replace('3DP_', '')} Printing</p>
                <p><span className="font-medium">Material:</span> {material}</p>
                <p><span className="font-medium">Finish:</span> Standard High-Quality</p>
              </div>
            </div>

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
        )}

        {/* DFM issues */}
        {response?.dfmIssues && response.dfmIssues.length > 0 && (
          <div className="border border-[#1E2A45] bg-[#0C1F3D]/50 p-4 h-full flex flex-col">
            <div className="mb-6 border border-[#F46036] bg-[#F46036]/10 p-4">
              <h3 className="text-xl font-andale mb-2 text-[#F46036]">Manufacturing Issues</h3>
              <p className="mb-4 text-white">The part cannot be manufactured due to the following issues:</p>
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
            </div>

            <div className="mt-4">
              <GlowButton onClick={handleReset}>Try Again</GlowButton>
            </div>
          </div>
        )}

        {!response?.success && !response?.dfmIssues && (
          <div className="border border-[#1E2A45] bg-[#0C1F3D]/50 p-4 h-full flex flex-col">
            <div className="mb-6">
              <h2 className="text-xl font-andale mb-4 text-white">Manufacturing Options</h2>

              <div className="flex flex-wrap gap-2 mb-4">
                <div className="relative">
                  <button
                    className="border border-[#5fe496] bg-[#5fe496]/20 text-[#5fe496] px-4 py-1 text-sm rounded-none"
                  >
                    3D Print
                  </button>
                </div>

                <div className="relative group">
                  <button className="text-white/50 border border-[#1E2A45] bg-[#0A1525] px-4 py-1 text-sm rounded-none opacity-50 cursor-not-allowed">
                    CNC
                  </button>
                  <div className="absolute bottom-full mb-2 right-0 hidden group-hover:block bg-[#0C1F3D] border border-[#1E2A45] p-2 rounded-none text-xs text-white/70 w-32 z-10 text-center">
                    Coming Soon!
                  </div>
                </div>

                <div className="relative group">
                  <button className="text-white/50 border border-[#1E2A45] bg-[#0A1525] px-4 py-1 text-sm rounded-none opacity-50 cursor-not-allowed">
                    Sheet Metal
                  </button>
                  <div className="absolute bottom-full mb-2 right-0 hidden group-hover:block bg-[#0C1F3D] border border-[#1E2A45] p-2 rounded-none text-xs text-white/70 w-32 z-10 text-center">
                    Coming Soon!
                  </div>
                </div>
              </div>

              <div className="text-white/70 text-sm font-avenir mb-2">
                <span className="text-[#5fe496]">Note:</span> All 3D printing services include standard high-quality finish and 10-day lead time.
              </div>
            </div>

            <div className="space-y-4 flex-grow">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <label className="block text-sm font-medium text-white font-avenir">Process</label>
                  <select
                    value={process}
                    onChange={(e) => handleProcessChange(e.target.value as ProcessType)}
                    className="w-full bg-[#0A1525] border border-[#1E2A45] text-white p-2 rounded-none focus:outline-none focus:ring-1 focus:ring-[#5fe496] font-avenir"
                  >
                    <option value="" disabled>Select process</option>
                    <option value="3DP_FDM">FDM</option>
                    <option value="3DP_SLA">SLA</option>
                    <option value="3DP_SLS">SLS</option>
                  </select>
                </div>

                <div className="space-y-2">
                  <label className="block text-sm font-medium text-white font-avenir">Material</label>
                  <select
                    value={material}
                    onChange={(e) => setMaterial(e.target.value)}
                    className="w-full bg-[#0A1525] border border-[#1E2A45] text-white p-2 rounded-none focus:outline-none focus:ring-1 focus:ring-[#5fe496] font-avenir"
                  >
                    <option value="" disabled>Select material</option>
                    {process === '3DP_FDM' && (
                      <>
                        <option value="pla">PLA</option>
                        <option value="abs">ABS</option>
                        <option value="petg">PETG</option>
                        <option value="tpu">TPU (Flexible)</option>
                      </>
                    )}
                    {process === '3DP_SLS' && (
                      <>
                        <option value="nylon12-white">Nylon 12 - White</option>
                        <option value="nylon12-black">Nylon 12 - Black</option>
                      </>
                    )}
                    {process === '3DP_SLA' && (
                      <>
                        <option value="standard-resin">Standard Resin</option>
                      </>
                    )}
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <label className="block text-sm font-medium text-white font-avenir">Quantity</label>
                  <input
                    type="number"
                    min="1"
                    defaultValue="1"
                    className="w-full bg-[#0A1525] border border-[#1E2A45] text-white p-2 rounded-none focus:outline-none focus:ring-1 focus:ring-[#5fe496] font-avenir"
                  />
                </div>

                <div className="space-y-2">
                  <label className="block text-sm font-medium text-white font-avenir">Finish</label>
                  <div className="w-full bg-[#0A1525] border border-[#1E2A45] text-white/70 p-2 rounded-none font-avenir flex items-center">
                    <span>Standard High-Quality</span>
                    <div className="ml-2 relative group cursor-help">
                      <Info className="h-4 w-4 text-white/50" />
                      <div className="absolute bottom-full mb-2 left-0 hidden group-hover:block bg-[#0C1F3D] border border-[#1E2A45] p-2 rounded-none text-xs text-white/70 w-48 z-10">
                        All 3D printing services include our standard high-quality finish.
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <div className="space-y-2 mt-4">
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
        )}
      </div>
    </div>
  );
}
