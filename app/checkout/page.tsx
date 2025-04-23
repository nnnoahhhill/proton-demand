"use client";

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useCart } from '@/lib/cart';
import { useLoading } from '@/lib/loading-context';
import { sendOrderNotification } from '@/lib/slack';
import { GlowButton } from '@/components/ui/glow-button';
import { loadStripe, StripeElementsOptions } from '@stripe/stripe-js';
import { Elements } from '@stripe/react-stripe-js';
import { createPaymentIntent } from '@/lib/api';
import Link from 'next/link';
import { ArrowLeft } from 'lucide-react';
import CheckoutForm from './CheckoutForm';

// Load Stripe outside component to avoid recreating on render
const stripePromise = loadStripe(process.env.NEXT_PUBLIC_STRIPE_PUBLIC_KEY || '');

export default function CheckoutPage() {
  const { items, totalPrice, subtotalPrice, shippingCost, clearCart, removeItem, updateQuantity } = useCart();
  const router = useRouter();
  const { showLoadingOverlay, hideLoadingOverlay } = useLoading();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [currentStep, setCurrentStep] = useState(1); // 1 = Shipping, 2 = Payment
  const [clientSecret, setClientSecret] = useState<string | null>(null);
  const [paymentIntentId, setPaymentIntentId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [paymentSuccessful, setPaymentSuccessful] = useState(false);

  // Form states
  const [formData, setFormData] = useState({
    // Shipping info
    fullName: '',
    email: '',
    phone: '',
    address: '',
    city: '',
    state: '',
    zipCode: '',
    country: 'US',
    specialInstructions: '',

    // Payment info
    cardNumber: '',
    cardName: '',
    expiryDate: '',
    cvv: '',
  });

  const [errors, setErrors] = useState<Record<string, string>>({});

  // Calculate total
  const subtotal = items.reduce((sum, item) => sum + item.price * item.quantity, 0);
  const shipping = shippingCost;
  const total = subtotal + shipping;

  // Handle form changes
  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));

    // Clear error when field is edited
    if (errors[name]) {
      setErrors(prev => {
        const newErrors = { ...prev };
        delete newErrors[name];
        return newErrors;
      });
    }
  };

  // Validate current step
  const validateStep = () => {
    const newErrors: Record<string, string> = {};

    if (currentStep === 1) {
      // Validate shipping info
      if (!formData.fullName) newErrors.fullName = 'Name is required';
      if (!formData.email) newErrors.email = 'Email is required';
      if (formData.email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) newErrors.email = 'Invalid email format';
      if (!formData.phone) newErrors.phone = 'Phone is required';
      if (!formData.address) newErrors.address = 'Address is required';
      if (!formData.city) newErrors.city = 'City is required';
      if (!formData.state) newErrors.state = 'State is required';
      if (!formData.zipCode) newErrors.zipCode = 'ZIP code is required';
    } else if (currentStep === 2) {
      // Validate payment info
      if (!formData.cardNumber) newErrors.cardNumber = 'Card number is required';
      if (formData.cardNumber && !/^\d{16}$/.test(formData.cardNumber.replace(/\s/g, ''))) {
        newErrors.cardNumber = 'Invalid card number';
      }
      if (!formData.cardName) newErrors.cardName = 'Name on card is required';
      if (!formData.expiryDate) newErrors.expiryDate = 'Expiry date is required';
      if (formData.expiryDate && !/^(0[1-9]|1[0-2])\/\d{2}$/.test(formData.expiryDate)) {
        newErrors.expiryDate = 'Invalid format (MM/YY)';
      }
      if (!formData.cvv) newErrors.cvv = 'CVV is required';
      if (formData.cvv && !/^\d{3,4}$/.test(formData.cvv)) {
        newErrors.cvv = 'Invalid CVV';
      }
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  // Navigate to next step
  const nextStep = () => {
    if (validateStep()) {
      setCurrentStep(prev => prev + 1);
    }
  };

  // Navigate to previous step
  const prevStep = () => {
    setCurrentStep(prev => prev - 1);
  };

  // Handle quantity change
  const handleQuantityChange = (id: string, newQuantity: number) => {
    if (newQuantity < 1) return;
    updateQuantity(id, newQuantity);
  };

  // Handle form submission
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!validateStep()) return;

    if (items.length === 0) {
      alert('Your cart is empty');
      return;
    }

    setIsSubmitting(true);
    showLoadingOverlay();

    try {
      // Generate a random order number
      const orderNumber = `ORD-${Math.floor(Math.random() * 1000000).toString().padStart(6, '0')}`;

      // Get model files for the notification
      // We need to retrieve the actual STL files for each quote
      let modelFilesForNotification: File[] = [];
      
      try {
        console.log("DEBUG: Starting to retrieve model files for Slack notification");
        for (const item of items) {
          if (localStorage && typeof window !== 'undefined') {
            // First check for basic file metadata
            const storedFileData = localStorage.getItem(`model_file_${item.id}`);
            console.log(`DEBUG: Retrieved stored file data for item ${item.id}:`, storedFileData);
            
            // Then check for enhanced metadata (from our new storage approach)
            const storedMetadata = localStorage.getItem(`model_file_metadata_${item.id}`);
            console.log(`DEBUG: Retrieved stored file metadata for item ${item.id}:`, storedMetadata);
            
            if (storedFileData || storedMetadata) {
              try {
                // Use enhanced metadata if available, otherwise fallback to basic data
                const fileData = storedMetadata ? JSON.parse(storedMetadata) : JSON.parse(storedFileData || '{}');
                console.log(`DEBUG: Parsed file data for ${item.id}:`, fileData);
                
                // Create a file with the correct name and quoteId
                const fileName = fileData.fileName || item.fileName;
                console.log(`DEBUG: Creating placeholder file with name ${fileName} and quoteId ${item.id}`);
                
                // Since we can't reliably store large files in localStorage, we create a small
                // placeholder file with the correct name. The actual file will be retrieved
                // from the server storage in the Slack notification handler.
                const placeholderContent = new Uint8Array([
                  // This is an ASCII string embedded in the file to indicate it's a placeholder
                  // that should be replaced with a server-side file
                  ...Array.from("SERVER_STORED_FILE:"+item.id).map(c => c.charCodeAt(0))
                ]);
                
                const modelFile = new File(
                  [placeholderContent],
                  fileName,
                  { 
                    type: fileData.fileType || 'model/stl',
                    lastModified: fileData.lastModified || Date.now()
                  }
                );
                
                // Add a special property to indicate this is a server-stored file
                // This will be checked in the Slack notification handler
                Object.defineProperty(modelFile, 'serverStored', {
                  value: true,
                  writable: false
                });
                
                // Also add the quote ID for reference
                Object.defineProperty(modelFile, 'quoteId', {
                  value: item.id,
                  writable: false
                });
                
                console.log(`DEBUG: Adding placeholder file to notification:`, modelFile.name, modelFile.size);
                modelFilesForNotification.push(modelFile);
              } catch (e) {
                console.error('Error parsing stored file data:', e);
              }
            } else {
              console.log(`DEBUG: No stored file data found for item ${item.id}`);
            }
          }
        }
        console.log(`DEBUG: Total model files for notification: ${modelFilesForNotification.length}`);
      } catch (e) {
        console.error('Error getting model files for notification:', e);
      }
      
      // Send order notification to Slack
      await sendOrderNotification({
        orderId: orderNumber,
        // Add quote IDs from cart items
        quoteId: items.length === 1 ? items[0].id : undefined, // Use first item's ID if only one item
        customerName: formData.fullName,
        customerEmail: formData.email,
        items: items.map(item => ({
          id: item.id,
          fileName: item.fileName,
          process: item.process,
          // Add technology if we have it
          technology: item.metadata?.technology || undefined,
          material: item.material,
          finish: item.finish,
          quantity: item.quantity,
          // We're not including price in Slack messages
        })),
        specialInstructions: formData.specialInstructions,
        shippingAddress: {
          line1: formData.address,
          city: formData.city,
          state: formData.state,
          postal_code: formData.zipCode,
          country: formData.country
        },
        // Add model files if we have them
        modelFiles: modelFilesForNotification.length > 0 ? modelFilesForNotification : undefined,
        // Set the order date
        orderDate: new Date()
      });

      // Simulate processing time
      await new Promise(resolve => setTimeout(resolve, 1500));

      // Clear the cart
      clearCart();

      // Redirect to success page
      router.push('/checkout/success');
    } catch (error) {
      console.error('Error processing order:', error);
      alert('There was a problem processing your order. Please try again.');
      hideLoadingOverlay();
    } finally {
      setIsSubmitting(false);
    }
  };

  // Function to handle successful payment (passed to CheckoutForm)
  const handlePaymentSuccess = (piId: string) => {
    console.log("Payment successful on page level:", piId);
    setPaymentSuccessful(true);
    setPaymentIntentId(piId);
    setError(null);
    setLoading(false);
    // It's generally safer to clear the cart after webhook confirmation,
    // but clearing it here provides faster feedback to the user.
    // clearCart(); 
  };

  // Function to handle errors during payment (passed to CheckoutForm)
  const handlePaymentError = (errorMessage: string) => {
      console.error("Payment error on page level:", errorMessage);
      setError(errorMessage);
      setLoading(false);
  };

  // Function to handle loading state changes (passed to CheckoutForm)
  const handleLoadingChange = (isLoading: boolean) => {
      setLoading(isLoading);
  };

  // Stripe Elements options - Minimal for now, can be expanded
  // The clientSecret will be managed within the CheckoutForm component usually
  const options: StripeElementsOptions = {
    // We don't pass clientSecret here if PaymentIntent is created on submit
    appearance: {
      theme: 'night', // Matches the site theme
      variables: {
        colorPrimary: '#5fe496',
        colorBackground: '#0C1F3D', // Slightly different from main bg for contrast?
        colorText: '#FFFFFF',
        colorDanger: '#F46036',
        fontFamily: '"Avenir Next", system-ui, sans-serif', // Match font
        borderRadius: '0px', // Match border radius
        colorTextPlaceholder: '#ffffff70',
      },
      rules: {
        '.Input': {
            backgroundColor: '#0A1525', // Input background
            border: '1px solid #1E2A45' // Input border
        }
      }
    },
  };

  if (paymentSuccessful) {
    return (
      <div className="flex flex-col min-h-screen bg-[#0A1525] text-white">
        <main className="flex-1 container py-10 flex flex-col items-center justify-center text-center">
          <h1 className="text-3xl font-andale text-[#5fe496] mb-4">Payment Successful!</h1>
          <p className="text-lg text-white/80 mb-6">Thank you for your order. We'll get started on it right away.</p>
          <p className="text-sm text-white/60 mb-8">Order Confirmation ID: {paymentIntentId || 'N/A'}</p>
          <Link href="/" className="text-[#5fe496] hover:underline font-avenir">
            Return to Homepage
          </Link>
          {/* Maybe add a link to an order history page later */}
        </main>
      </div>
    );
  }

  // If cart is empty, show a message
  if (items.length === 0) {
    return (
      <div className="container px-4 md:px-6 py-12">
        <div className="max-w-3xl mx-auto text-center">
          <h1 className="text-3xl font-andale mb-6">Your Cart is Empty</h1>
          <p className="text-white/70 mb-8 font-avenir">
            You haven't added any items to your cart yet.
          </p>
          <GlowButton asChild>
            <a href="/quote">Get a Quote</a>
          </GlowButton>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col min-h-screen bg-[#0A1525] text-white">
      <header className="py-4 border-b border-[#1E2A45]">
        <div className="container flex items-center justify-between">
           <Link href="/quote" className="flex items-center text-white hover:text-[#5fe496] transition-colors">
             <ArrowLeft className="h-5 w-5 mr-2" />
             Back to Quote
           </Link>
           <h1 className="text-2xl font-andale">Checkout</h1>
           {/* Placeholder for maybe a logo */}
           <div></div>
        </div>
      </header>

      <main className="flex-1 container py-10">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-12">
          {/* Left side: Order Summary */}
          <div className="space-y-6">
            <h2 className="text-xl font-andale border-b border-[#1E2A45] pb-2 mb-4">Order Summary</h2>
            {items.length === 0 ? (
              <p className="text-white/70">Your cart is empty.</p>
            ) : (
              <ul className="space-y-4">
                {items.map(item => (
                  <li key={item.id} className="flex justify-between items-center text-sm">
                    <div>
                      <p className="font-medium font-avenir">{item.fileName} (x{item.quantity})</p>
                      <p className="text-xs text-white/60">{item.process} / {item.material}</p>
                    </div>
                    <p className="font-avenir">${(item.price * item.quantity).toFixed(2)}</p>
                  </li>
                ))}
              </ul>
            )}
            {items.length > 0 && (
              <div className="border-t border-[#1E2A45] pt-4 space-y-2 text-sm">
                <div className="flex justify-between">
                  <p className="text-white/70">Subtotal</p>
                  <p>${subtotal.toFixed(2)}</p>
                </div>
                <div className="flex justify-between">
                  <p className="text-white/70">Shipping</p>
                  <p>${shipping.toFixed(2)}</p>
                </div>
                <div className="flex justify-between font-bold text-base">
                  <p>Total</p>
                  <p>${total.toFixed(2)}</p>
                </div>
              </div>
            )}
          </div>

          {/* Right side: Checkout Form */}
          <div className="space-y-6">
            <h2 className="text-xl font-andale border-b border-[#1E2A45] pb-2 mb-4">Shipping & Payment</h2>
            {/* Stripe Elements Provider wraps the form */} 
            <Elements stripe={stripePromise} options={options}>
              {/* Pass cart items and callbacks to the form */}
              <CheckoutForm
                totalAmount={total}
                onPaymentSuccess={handlePaymentSuccess}
                onPaymentError={handlePaymentError}
                onLoadingChange={handleLoadingChange}
                shippingCost={shipping}
              />
            </Elements>
            {/* Display loading/error messages triggered by CheckoutForm */} 
             {loading && (
                <p className="text-sm text-white/70 mt-2">Processing payment...</p>
             )}
             {error && (
                <p className="text-sm text-[#F46036] mt-2">Error: {error}</p>
             )}
          </div>
        </div>
      </main>

      {/* Footer (optional) */}
      {/* ... */}
    </div>
  );
}
