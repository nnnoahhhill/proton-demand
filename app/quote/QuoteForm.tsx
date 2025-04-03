"use client";

import { useState, useRef, FormEvent, ChangeEvent } from "react";
import { getQuote, materialOptions, finishOptions, QuoteResponse, DFMIssue } from "@/lib/api";
import { GlowButton } from "@/components/ui/glow-button";
import { useCart } from "@/lib/cart";
import { useRouter } from "next/navigation";

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

export default function QuoteForm() {
  const [process, setProcess] = useState<ProcessType>('CNC');
  const [material, setMaterial] = useState<string>('');
  const [finish, setFinish] = useState<string>('');
  const [modelFile, setModelFile] = useState<File | null>(null);
  const [drawingFile, setDrawingFile] = useState<File | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [response, setResponse] = useState<QuoteResponse | null>(null);
  const [error, setError] = useState<string>('');
  const [addedToCart, setAddedToCart] = useState(false);
  
  // Get cart context
  const { addItem } = useCart();
  const router = useRouter();
  
  // Refs for the file inputs
  const modelFileRef = useRef<HTMLInputElement>(null);
  const drawingFileRef = useRef<HTMLInputElement>(null);
  
  // Handle process change
  const handleProcessChange = (e: ChangeEvent<HTMLSelectElement>) => {
    const newProcess = e.target.value as ProcessType;
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
    <div className="glow-card rounded-none border border-[#1E2A45] bg-[#0C1F3D]/30 p-8 backdrop-blur-sm">
      <h2 className="text-2xl font-andale mb-6">Get Manufacturing Quote</h2>
      
      {/* Error message */}
      {error && (
        <div className="mb-6 p-4 border border-[#F46036] bg-[#F46036]/10 text-[#F46036]">
          {error}
        </div>
      )}
      
      {/* Success message */}
      {response?.success && (
        <div className="mb-6 p-4 border border-[#5fe496] bg-[#5fe496]/10 text-[#5fe496]">
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
        <div className="mb-6 p-4 border border-[#F46036] bg-[#F46036]/10">
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
      
      {/* Quote form */}
      {!response?.success && !response?.dfmIssues && (
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Process selection */}
          <div>
            <label className="block text-white/70 mb-2 font-avenir">Manufacturing Process</label>
            <select
              value={process}
              onChange={handleProcessChange}
              className="w-full bg-[#0A1525] border border-[#1E2A45] p-3 rounded-none text-white font-avenir"
              required
            >
              <option value="">Select a process</option>
              {processOptions.map((option: Option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>
          
          {/* Material selection */}
          <div>
            <label className="block text-white/70 mb-2 font-avenir">Material</label>
            <select
              value={material}
              onChange={(e) => setMaterial(e.target.value)}
              className="w-full bg-[#0A1525] border border-[#1E2A45] p-3 rounded-none text-white font-avenir"
              required
              disabled={!process}
            >
              <option value="">Select a material</option>
              {materialOptions[process]?.map((option: Option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>
          
          {/* Finish selection */}
          <div>
            <label className="block text-white/70 mb-2 font-avenir">Surface Finish</label>
            <select
              value={finish}
              onChange={(e) => setFinish(e.target.value)}
              className="w-full bg-[#0A1525] border border-[#1E2A45] p-3 rounded-none text-white font-avenir"
              required
              disabled={!process}
            >
              <option value="">Select a finish</option>
              {finishOptions[process]?.map((option: Option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>
          
          {/* Model file upload */}
          <div>
            <label className="block text-white/70 mb-2 font-avenir">3D Model File (STL or STEP)</label>
            <input
              type="file"
              ref={modelFileRef}
              onChange={handleModelFileChange}
              accept=".stl,.step,.stp"
              className="w-full bg-[#0A1525] border border-[#1E2A45] p-3 rounded-none text-white font-avenir"
              required
            />
            <p className="text-white/50 text-sm mt-1 font-avenir">
              Upload a 3D model file in STL or STEP format
            </p>
          </div>
          
          {/* Optional drawing file upload */}
          <div>
            <label className="block text-white/70 mb-2 font-avenir">Engineering Drawing (Optional, PDF)</label>
            <input
              type="file"
              ref={drawingFileRef}
              onChange={handleDrawingFileChange}
              accept=".pdf"
              className="w-full bg-[#0A1525] border border-[#1E2A45] p-3 rounded-none text-white font-avenir"
            />
            <p className="text-white/50 text-sm mt-1 font-avenir">
              Upload an engineering drawing in PDF format (optional)
            </p>
          </div>
          
          {/* Submit button */}
          <div>
            <GlowButton
              type="submit"
              disabled={loading}
              className="w-full justify-center"
            >
              {loading ? 'Processing...' : 'Get Quote'}
            </GlowButton>
          </div>
        </form>
      )}
    </div>
  );
} 