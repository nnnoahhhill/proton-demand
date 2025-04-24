"use client";

import { useState, useRef, FormEvent, ChangeEvent, useEffect } from "react";
import {
  getQuote,
  materialOptions,
  finishOptions,
  QuoteResponse,
  DFMIssue,
  createCheckoutSession
} from "@/lib/api";
import { GlowButton } from "@/components/ui/glow-button";
import { useCart } from "@/lib/cart";
import { useRouter } from "next/navigation";
import { ModelViewer } from "@/components/model-viewer";
import { Spinner } from "@/components/ui/spinner";
import { FileUp, Info, RotateCw, Eye, EyeOff } from "lucide-react";
import { loadStripe } from '@stripe/stripe-js';

// Define the process type for stricter typing
// Use values matching the backend ManufacturingProcess enum
type ProcessType = '3D Printing' | 'CNC Machining' | 'Sheet Metal';

// Define option type
interface Option {
  value: string;
  label: string;
}

export default function NewQuoteForm() {
  const [manufacturingProcess, setManufacturingProcess] = useState<ProcessType>('3D Printing');
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
  const [isCheckingOut, setIsCheckingOut] = useState(false);
  const [checkoutError, setCheckoutError] = useState('');
  const [quantity, setQuantity] = useState<number>(1);

  // Get cart context
  const { addItem } = useCart();
  const router = useRouter();

  // Refs for the file inputs
  const modelFileRef = useRef<HTMLInputElement>(null);
  const drawingFileRef = useRef<HTMLInputElement>(null);

  // Initialize Stripe outside the component rendering cycle
  const stripePromise = process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY
    ? loadStripe(process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY)
    : null;

  // Define 3D printing technology type for stricter typing
  type PrintTechnology = 'FDM' | 'SLA' | 'SLS';

  // State for 3D printing technology
  const [printTechnology, setPrintTechnology] = useState<PrintTechnology | ''>('');

  // Handle process change
  const handleProcessChange = (value: ProcessType) => {
    setManufacturingProcess(value);
    // Reset material and finish when process changes
    setMaterial('');
    setFinish('');
  };

  // Handle 3D printing technology change
  const handleTechnologyChange = (value: PrintTechnology | '') => {
    setPrintTechnology(value);
    // Reset material when technology changes
    setMaterial('');
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
      if (!fileExtension || !['stl', 'step', 'stp', 'obj'].includes(fileExtension)) {
        setError('Please upload a valid 3D model file (.stl, .step, .stp, or .obj).');
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
    if (!manufacturingProcess) {
      setError('Please select a manufacturing process');
      return;
    }

    if (!printTechnology) {
      setError('Please select a printing technology (FDM, SLA, or SLS)');
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
      if (manufacturingProcess === '3D Printing') {
        setFinish('standard');
      }
    }

    console.log("Submitting form with:",
      "process=", manufacturingProcess,
      "technology=", printTechnology,
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
    setCheckoutError('');

    try {
      // Get quote from API
      // Always use standard finish for 3D printing
      const standardFinish = 'standard';

      // First attempt
      let quoteResponse = await getQuote({
        process: manufacturingProcess,
        technology: manufacturingProcess === '3D Printing' ? printTechnology : undefined,
        material,
        finish: standardFinish,
        modelFile,
        drawingFile: drawingFile || undefined
      });

      // Handle timeout or connection errors with a retry
      if (!quoteResponse.success && 
          (quoteResponse.error_message?.includes('timeout') || 
           quoteResponse.error_message?.includes('network') ||
           quoteResponse.error_message?.includes('failed'))) {
        
        console.log("Retrying quote request after initial failure...");
        setError('Connection issue detected. Retrying...');
        
        // Wait 2 seconds before retry
        await new Promise(resolve => setTimeout(resolve, 2000));
        
        // Second attempt
        quoteResponse = await getQuote({
          process: manufacturingProcess,
          technology: manufacturingProcess === '3D Printing' ? printTechnology : undefined,
          material,
          finish: standardFinish,
          modelFile,
          drawingFile: drawingFile || undefined
        });
      }

      console.log("API response:", quoteResponse);

      // Set response REGARDLESS of success, so DFM issues can be displayed
      setResponse(quoteResponse);

      // --- SIMPLIFIED ERROR HANDLING --- 
      // If success is false, display the error message from the backend.
      // If success is true, any DFM issues will be shown in their own section.
      if (!quoteResponse.success) {
        const errMsg = quoteResponse.error_message || 'Unknown error occurred during quote generation.';
        console.error("Quote generation failed:", errMsg);
        setError(errMsg);
      } else {
        // Clear any previous generic errors if successful
        setError(''); 
      }
      // --- END SIMPLIFIED ERROR HANDLING ---
      
      // Removed the complex error checking logic based on DFM issues

    } catch (err) {
      console.error('Error submitting quote form:', err);
      // Handle client-side fetch errors (network, etc.)
      setError(err instanceof Error ? `Network/Fetch Error: ${err.message}` : 'An unknown client-side error occurred');
      // Ensure response state is cleared on fetch error
      setResponse(null);
    } finally {
      setLoading(false);
    }
  };

  // Add to cart
  const handleAddToCart = () => {
    if (response && response.success && modelFile) {
      // Initialize baseQuoteId - if this is the first part for this order
      // Get or extract the base quote ID
      let baseQuoteId = response.quote_id;
      let suffix = '';
      
      try {
        // Check if we can find any existing cart items with the same base ID
        // This check helps us determine if this is a new or existing order
        const storedCart = localStorage.getItem('protondemand_cart');
        if (storedCart) {
          const cartItems = JSON.parse(storedCart);
          
          // Look for any item that might have this quote ID as a base
          const matchingItems = cartItems.filter((item: any) => {
            // Either this is the base already
            return (item.baseQuoteId && item.baseQuoteId === response.quote_id) ||
              // OR the base is a prefix of this ID
              (response.quote_id.startsWith(item.baseQuoteId + '-'));
          });
          
          if (matchingItems.length > 0) {
            // We found existing items - use their baseQuoteId
            baseQuoteId = matchingItems[0].baseQuoteId;
            console.log(`DEBUG: Using existing base quote ID: ${baseQuoteId}`);
          } else {
            // This is a new order - use quote_id as baseQuoteId
            console.log(`DEBUG: Using new base quote ID: ${baseQuoteId}`);
          }
        } else {
          console.log(`DEBUG: No existing cart, using quote ID as base: ${baseQuoteId}`);
        }
        
        // Store model file info in localStorage for later use in order processing
        console.log("DEBUG: Storing model file info for quote:", response.quote_id);
        
        // Calculate weight in kg
        const weightInGrams = response.cost_estimate?.material_weight_g || 100;
        const weightInKg = weightInGrams / 1000;
        
        // Store additional metadata about the file
        const fileMetadata = {
          fileName: modelFile.name,
          fileSize: modelFile.size,
          fileType: modelFile.type || 'model/stl',
          lastModified: modelFile.lastModified,
          quoteId: response.quote_id,
          baseQuoteId: baseQuoteId,
          suffix: suffix,
          technology: printTechnology,
          // Add weight data for shipping calculations
          weight_g: weightInGrams,
          volume_cm3: response.cost_estimate?.total_volume_cm3 || 0,
          // Store a flag indicating we need to get the file from the server instead
          serverStored: true
        };
        
        localStorage.setItem(`model_file_metadata_${response.quote_id}`, JSON.stringify(fileMetadata));
        console.log(`DEBUG: Stored model file metadata for quote ${response.quote_id}`);
        
        // We need to upload the file to the server for later access
        try {
          // Create a form data object to send the file
          const formData = new FormData();
          formData.append('file', modelFile);
          formData.append('quoteId', response.quote_id);
          formData.append('baseQuoteId', baseQuoteId);
          formData.append('suffix', suffix);
          formData.append('technology', printTechnology || 'unknown');
          formData.append('quantity', String(quantity)); // Add quantity to form data
          
          // Always add material regardless of technology
          formData.append('material', material || 
            (printTechnology === 'FDM' ? 'PLA' : 
             printTechnology === 'SLA' ? 'Standard Resin' : 
             printTechnology === 'SLS' ? 'Nylon' : 'Standard'));
                   
          // Add FFF/FDM specific data for slicing configuration
          if (printTechnology === 'FDM') {
            formData.append('fff_configured', 'true');
            if (response.cost_estimate) {
              formData.append('weight_g', String(response.cost_estimate.material_weight_g || 0));
              formData.append('volume_cm3', String(response.cost_estimate.total_volume_cm3 || 0));
            }
          } else {
            formData.append('fff_configured', 'false');
          }
          
          // Send the file to the server with retry logic for ECONNRESET errors
          console.log(`DEBUG: Uploading model file to server for quote ${response.quote_id}`);
          
          // Create a function that can be called recursively for retries
          const uploadModelWithRetry = async (retryCount = 0, maxRetries = 3) => {
            try {
              console.log(`DEBUG: Model upload attempt ${retryCount + 1} of ${maxRetries + 1}`);
              
              // Add a small random delay between retries to avoid timing conflicts
              if (retryCount > 0) {
                const delay = 500 + Math.random() * 1000; // Random delay between 500-1500ms
                console.log(`DEBUG: Waiting ${delay.toFixed(0)}ms before retry #${retryCount}`);
                await new Promise(resolve => setTimeout(resolve, delay));
              }
              
              // Create a new FormData for each attempt to avoid stale/consumed data
              const retryFormData = new FormData();
              retryFormData.append('file', modelFile);
              retryFormData.append('quoteId', response.quote_id);
              retryFormData.append('baseQuoteId', baseQuoteId);
              retryFormData.append('suffix', suffix);
              retryFormData.append('technology', printTechnology || 'unknown');
              retryFormData.append('quantity', String(quantity));
              
              // Always add material regardless of technology
              retryFormData.append('material', material || 
                (printTechnology === 'FDM' ? 'PLA' : 
                 printTechnology === 'SLA' ? 'Standard Resin' : 
                 printTechnology === 'SLS' ? 'Nylon' : 'Standard'));
                       
              // Add FFF/FDM specific data for slicing configuration
              if (printTechnology === 'FDM') {
                retryFormData.append('fff_configured', 'true');
                if (response.cost_estimate) {
                  retryFormData.append('weight_g', String(response.cost_estimate.material_weight_g || 0));
                  retryFormData.append('volume_cm3', String(response.cost_estimate.total_volume_cm3 || 0));
                }
              } else {
                retryFormData.append('fff_configured', 'false');
              }
              
              // Create a fetch request with timeout
              const controller = new AbortController();
              const timeoutId = setTimeout(() => controller.abort(), 30000); // 30 second timeout
              
              const fetchResponse = await fetch('/api/upload-model', {
                method: 'POST',
                body: retryFormData,
                signal: controller.signal
              });
              
              clearTimeout(timeoutId); // Clear timeout if fetch completes
              
              if (!fetchResponse.ok) {
                const errorData = await fetchResponse.json();
                throw new Error(errorData.error || 'Server returned an error');
              }
              
              const data = await fetchResponse.json();
              console.log(`DEBUG: Server upload response:`, data);
              
              // Update metadata with server path
              if (data.success && data.filePath) {
                const updatedMetadata = {
                  ...fileMetadata,
                  serverFilePath: data.filePath,
                  orderFolderPath: data.orderFolderPath,
                  uploadTime: new Date().toISOString(),
                  processingTime: data.processingTime || null
                };
                localStorage.setItem(`model_file_metadata_${response.quote_id}`, JSON.stringify(updatedMetadata));
                console.log(`DEBUG: Updated model metadata with server paths`);
              }
              
              return data;
            } catch (error) {
              console.error(`DEBUG: Error uploading file to server (attempt ${retryCount + 1}):`, error);
              
              // Check if we should retry
              const errorMessage = error instanceof Error ? error.message.toLowerCase() : '';
              const isConnectionError = 
                errorMessage.includes('reset') || 
                errorMessage.includes('econnreset') ||
                errorMessage.includes('aborted') ||
                errorMessage.includes('timeout') ||
                errorMessage.includes('network') ||
                (error as any)?.code === 'ECONNRESET';
              
              // If it's a connection error and we haven't exceeded max retries
              if (isConnectionError && retryCount < maxRetries) {
                console.log(`DEBUG: Connection error detected, will retry upload (${retryCount + 1}/${maxRetries})`);
                return uploadModelWithRetry(retryCount + 1, maxRetries);
              }
              
              // Otherwise, fail permanently
              console.error(`DEBUG: Upload failed after ${retryCount + 1} attempts:`, error);
              
              // Still store metadata even if upload failed - we'll mark it as failed
              const failedMetadata = {
                ...fileMetadata,
                uploadFailed: true,
                uploadError: error instanceof Error ? error.message : String(error),
                failedAttempts: retryCount + 1,
                lastAttemptTime: new Date().toISOString()
              };
              localStorage.setItem(`model_file_metadata_${response.quote_id}`, JSON.stringify(failedMetadata));
              
              throw error; // Re-throw to be caught by outer catch
            }
          };
          
          // Execute the upload with retry function
          uploadModelWithRetry()
            .then(data => {
              console.log(`DEBUG: Model upload completed successfully`);
            })
            .catch(finalError => {
              // This will only be called if all retries fail
              console.error(`DEBUG: All upload attempts failed:`, finalError);
              // Continue with the checkout flow anyway - we'll need to handle missing models later
            });
        } catch (uploadError) {
          console.error(`DEBUG: Error preparing file upload:`, uploadError);
        }
        
        // Create a cart item with base quote ID
        const cartItem = {
          id: response.quote_id,
          baseQuoteId: baseQuoteId,
          suffix: suffix,
          fileName: modelFile.name,
          process: response.process || manufacturingProcess,
          technology: printTechnology,
          material: response.material_info?.name || material,
          finish: finish,
          price: response.customer_price || 0,
          currency: response.material_info?.currency || 'USD',
          quantity: quantity,
          weightInKg: weightInKg
        };
        
        // Pass the cart item to addItem
        addItem(cartItem);
        setAddedToCart(true);
        setCheckoutError('');
      } catch (e) {
        console.error('Error storing model file info or adding to cart:', e);
      }
    }
  };

  // Proceed to checkout
  const handleCheckout = async () => {
    if (!response || !response.success || !response.customer_price || !modelFile || !stripePromise) {
      console.error('Checkout prerequisites not met:', { response, modelFile, stripePromise });
      setCheckoutError(
        !stripePromise
          ? 'Stripe is not configured correctly. Please check your environment variables.'
          : response?.error_message || 'Cannot proceed to checkout. Please ensure you have a valid quote.'
      );
      return;
    }

    // Check if FFF/FDM technology is selected but missing configuration
    if (printTechnology === 'FDM' && (!response.cost_estimate || !response.material_info)) {
      console.error('Missing FFF configuration for FDM print');
      setCheckoutError('Missing slicer configuration for FDM printing. Please try again or contact support.');
      return;
    }

    setIsCheckingOut(true);
    setCheckoutError('');

    try {
      // Calculate shipping cost based on weight ($20/kg)
      // Get weight in kg (convert from grams)
      const weightInKg = response.cost_estimate?.material_weight_g 
        ? response.cost_estimate.material_weight_g / 1000 
        : 0.1; // Default to 100g if weight is unknown
      
      const shippingCost = Math.max(5, weightInKg * 20 * quantity); // Minimum $5 shipping
      
      // 1. Call backend to create a checkout session
      const checkoutResponse = await createCheckoutSession({
        item_name: `Quote ${response.quote_id.substring(0, 8)} - ${modelFile.name}`,
        price: response.customer_price,
        currency: response.material_info?.currency || 'usd',
        quantity: quantity,
        quote_id: response.quote_id,
        file_name: modelFile.name,
        shipping_cost: shippingCost
      });

      if (checkoutResponse.error || !checkoutResponse.sessionId) {
        console.error("Failed to create checkout session:", checkoutResponse.error);
        setCheckoutError(checkoutResponse.error || 'Failed to initiate payment session.');
        setIsCheckingOut(false);
        return;
      }

      // 2. Redirect to Stripe Checkout
      const stripe = await stripePromise;
      if (!stripe) {
        console.error('Stripe.js failed to load.');
        setCheckoutError('Payment gateway failed to load. Please try again.');
        setIsCheckingOut(false);
        return;
      }

      const { error } = await stripe.redirectToCheckout({
        sessionId: checkoutResponse.sessionId,
      });

      // If redirectToCheckout fails (e.g., network error), show an error message
      if (error) {
        console.error('Stripe redirect error:', error);
        setCheckoutError(error.message || 'Failed to redirect to payment page.');
      }
      // No need to set isCheckingOut(false) here, as the user should be redirected
    } catch (err) {
      console.error('Error during checkout process:', err);
      setCheckoutError(err instanceof Error ? err.message : 'An unknown error occurred during checkout.');
      setIsCheckingOut(false);
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

  useEffect(() => {
    if (checkoutError) {
      const timer = setTimeout(() => {
        setCheckoutError('');
      }, 6000); // Longer timeout for checkout errors
      return () => clearTimeout(timer);
    }
  }, [checkoutError]);

  // Reset the form
  const handleReset = () => {
    setManufacturingProcess('3D Printing');
    setPrintTechnology('');
    setMaterial('');
    setFinish('standard'); // Keep standard finish
    setModelFile(null);
    setDrawingFile(null);
    setResponse(null);
    setError('');
    setAddedToCart(false);
    setCheckoutError('');
    setQuantity(1);

    // Reset file inputs
    if (modelFileRef.current) modelFileRef.current.value = '';
    if (drawingFileRef.current) drawingFileRef.current.value = '';
  };

  return (
    <div className="grid gap-6 md:grid-cols-2 relative">
      {/* Loading overlay - Conditionally include checkout loading */}
      {(loading || isCheckingOut) && (
        <div className="absolute inset-0 bg-[#0A1525]/80 backdrop-blur-sm z-10 flex items-center justify-center">
          <div className="flex flex-col items-center justify-center p-8 rounded-lg">
            <Spinner size={120} />
            <p className="mt-6 text-xl text-white font-andale">
              {isCheckingOut ? 'Redirecting to secure payment...' : 'Analyzing your model...'}
            </p>
            <p className="mt-2 text-white/70 font-avenir">
              {isCheckingOut ? 'Please wait' : 'This may take a few moments'}
            </p>
          </div>
        </div>
      )}
      {/* Left Column - Model Upload */}
      <div>
        <div className="border border-[#1E2A45] bg-[#0C1F3D]/50 p-4 mb-4 h-full flex flex-col">
          <h2 className="text-xl font-andale mb-4 text-white">Upload Your 3D Model</h2>

          <div className="flex-grow flex flex-col">
            <div className="flex-grow">
              <div className="flex items-center justify-center w-full h-[calc(100%-10px)]">
                {modelFile ? (
                  <div className="w-full h-full">
                    <div className="relative h-[400px]">
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
        {/* Error message - Show general error OR checkout error */}
        {(error || checkoutError) && (
          <div className="absolute top-1/4 left-1/2 transform -translate-x-1/2 z-50 p-4 border border-[#F46036] bg-[#0A1525] text-[#F46036] font-avenir shadow-lg max-w-md transition-opacity duration-300 ease-in-out opacity-90 hover:opacity-100">
            <div className="flex justify-between items-start">
              <div>{checkoutError || error}</div>
              <button
                onClick={() => {
                  setError('');
                  setCheckoutError('');
                }}
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
                <div className="grid grid-template-columns-fixed gap-y-2">
                  <p className="font-medium whitespace-nowrap">Quote ID:</p>
                  <p>{response.quote_id}</p>
                  
                  <p className="font-medium whitespace-nowrap">Price:</p>
                  <p className="whitespace-nowrap">
                    ${(response.customer_price! * quantity).toFixed(2)} {response.material_info?.currency || 'USD'}
                    {quantity > 1 && <span className="ml-2 text-white/60">(${response.customer_price?.toFixed(2)}/ea)</span>}
                  </p>
                  
                  <p className="font-medium whitespace-nowrap">Shipping:</p>
                  <p className="whitespace-nowrap">
                    ${(Math.max(5, (response.cost_estimate?.material_weight_g ? response.cost_estimate.material_weight_g / 1000 : 0.1) * 20 * quantity)).toFixed(2)} {response.material_info?.currency || 'USD'}
                  </p>
                  
                  <p className="font-medium whitespace-nowrap">Total:</p>
                  <p className="whitespace-nowrap font-bold">
                    ${(response.customer_price! * quantity + Math.max(5, (response.cost_estimate?.material_weight_g ? response.cost_estimate.material_weight_g / 1000 : 0.1) * 20 * quantity)).toFixed(2)} {response.material_info?.currency || 'USD'}
                  </p>
                  
                  <p className="font-medium whitespace-nowrap">Quantity:</p>
                  <p>{quantity}</p>
                  
                  <p className="font-medium whitespace-nowrap">Lead Time:</p>
                  <p>~10 business days</p>
                  
                  <p className="font-medium whitespace-nowrap">Process:</p>
                  <p>{response.process}</p>
                  
                  <p className="font-medium whitespace-nowrap">Technology:</p>
                  <p>{response.technology || printTechnology}</p>
                  
                  <p className="font-medium whitespace-nowrap">Material:</p>
                  <p>{response.material_info?.name || 'N/A'}</p>
                  
                  <p className="font-medium whitespace-nowrap">Finish:</p>
                  <p>Standard High-Quality</p>
                </div>
              </div>

              <style jsx>{`
                .grid-template-columns-fixed {
                  display: grid;
                  grid-template-columns: max-content 1fr;
                  column-gap: 1.75rem;
                }
              `}</style>
            </div>

            <div className="mt-4 flex justify-center items-center space-x-4">
              <GlowButton
                onClick={handleReset}
                className="bg-[#1e87d6] text-white hover:bg-[#1e87d6]/80"
              >
                New Quote
              </GlowButton>

              {addedToCart ? (
                <GlowButton
                  onClick={() => router.push('/cart')}
                  className="bg-[#5fe496] text-[#0A1525] hover:bg-[#5fe496]/80"
                >
                  View Cart
                </GlowButton>
              ) : (
                <GlowButton
                  onClick={handleAddToCart}
                  className="bg-[#5fe496] text-[#0A1525] hover:bg-[#5fe496]/80"
                >
                  Add to Cart
                </GlowButton>
              )}

              {addedToCart && (
                <GlowButton
                  onClick={handleCheckout}
                  className="bg-[#F46036] text-white hover:bg-[#F46036]/80"
                >
                  Checkout Now
                </GlowButton>
              )}
            </div>
          </div>
        )}

        {/* Original Quote Form - Render only if NO response exists yet */}
        {!response && (
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
                  <label className="block text-sm font-medium text-white font-avenir">Technology</label>
                  <select
                    value={printTechnology}
                    onChange={(e) => handleTechnologyChange(e.target.value as PrintTechnology)}
                    className="w-full bg-[#0A1525] border border-[#1E2A45] text-white p-2 rounded-none focus:outline-none focus:ring-1 focus:ring-[#5fe496] font-avenir"
                  >
                    <option value="" disabled>Select technology</option>
                    <option value="FDM">FDM</option>
                    <option value="SLA">SLA</option>
                    <option value="SLS">SLS</option>
                  </select>
                </div>

                <div className="space-y-2">
                  <label className="block text-sm font-medium text-white font-avenir">Material</label>
                  <select
                    value={material}
                    onChange={(e) => setMaterial(e.target.value)}
                    className="w-full bg-[#0A1525] border border-[#1E2A45] text-white p-2 rounded-none focus:outline-none focus:ring-1 focus:ring-[#5fe496] font-avenir"
                    disabled={!printTechnology}
                  >
                    <option value="" disabled>Select material</option>
                    
                    {printTechnology === 'FDM' && (
                      <>
                        <option value="fdm_pla_standard">PLA</option>
                        <option value="fdm_abs_standard">ABS</option>
                        <option value="fdm_petg_standard">PETG</option>
                        <option value="fdm_tpu_flexible">TPU (Flexible)</option>
                        <option value="fdm_nylon12_standard">Nylon 12</option>
                        <option value="fdm_asa_standard">ASA</option>
                      </>
                    )}
                    
                    {printTechnology === 'SLS' && (
                      <>
                        <option value="sls_nylon12_white">Nylon 12 White</option>
                        <option value="sls_nylon12_black">Nylon 12 Black</option>
                      </>
                    )}
                    
                    {printTechnology === 'SLA' && (
                      <>
                        <option value="sla_resin_standard">Standard Resin</option>
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
                    value={quantity}
                    onChange={(e) => setQuantity(Math.max(1, parseInt(e.target.value) || 1))}
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
                <GlowButton onClick={handleSubmit} className="w-full bg-[#F46036] text-white hover:bg-[#F46036]/80" disabled={loading}>
                  Generate Quote
                </GlowButton>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
