"use client";

import { useState, FormEvent } from 'react';
import { useStripe, useElements, CardElement } from '@stripe/react-stripe-js';
import { GlowButton } from '@/components/ui/glow-button';
import { createPaymentIntent, PaymentIntentResponse, SimpleCartItem } from '@/lib/api';
import { useCart } from '@/lib/cart';
import { Spinner } from "@/components/ui/spinner";

interface CheckoutFormProps {
  totalAmount: number;
  onPaymentSuccess: (paymentIntentId: string) => void;
  onPaymentError: (errorMessage: string) => void;
  onLoadingChange: (isLoading: boolean) => void;
  shippingCost: number;
}

const cardElementOptions = {
  style: {
    base: {
      fontSize: '16px',
      color: '#FFFFFF',
      '::placeholder': {
        color: 'rgba(255, 255, 255, 0.7)',
      },
      iconColor: '#FFFFFF',
      fontFamily: '"Avenir Next", system-ui, sans-serif',
    },
    invalid: {
      color: '#F46036',
      iconColor: '#F46036',
    },
  },
  hidePostalCode: true,
};

export default function CheckoutForm({ 
  totalAmount, 
  onPaymentSuccess, 
  onPaymentError, 
  onLoadingChange,
  shippingCost
}: CheckoutFormProps) {
  const stripe = useStripe();
  const elements = useElements();
  const { items, clearCart } = useCart();
  
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [email, setEmail] = useState('');
  const [name, setName] = useState('');
  const [couponCode, setCouponCode] = useState('');
  const [discount, setDiscount] = useState(0);
  const [isTestMode, setIsTestMode] = useState(false);
  const [discountedAmount, setDiscountedAmount] = useState(totalAmount);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);

    if (!stripe || !elements) {
      console.error("Stripe.js has not loaded yet.");
      onPaymentError("Payment gateway is not ready. Please wait and try again.");
      return;
    }

    const cardElement = elements.getElement(CardElement);
    if (!cardElement) {
        console.error("Card Element not found.");
        onPaymentError("Payment input is missing. Please refresh the page.");
        return;
    }
    
    if (!email || !name) {
      setErrorMessage("Please enter your name and email.");
      return;
    }

    onLoadingChange(true);

    try {
      const orderItems: SimpleCartItem[] = items.map(item => ({
        id: item.id,
        name: item.fileName,
        quantity: item.quantity,
        price: item.price 
      }));

      // Add shipping as a separate item
      if (shippingCost > 0) {
        orderItems.push({
          id: 'shipping',
          name: 'Shipping & Handling',
          quantity: 1,
          price: shippingCost
        });
      }
      
      // Collect quote IDs from cart items
      const quoteIds = items.map(item => item.id).filter(Boolean);
      
      // Collect information from the first item (we currently only handle one item)
      const firstItem = items[0];
      const technology = firstItem.technology || '';
      const material = firstItem.material || '';
      
      // Get quote ID for the main metadata (use first item's ID)
      const primaryQuoteId = firstItem.id || '';
      
      // Get file name for the main metadata
      const primaryFileName = firstItem.fileName || 'Unknown File';
      
      console.log(`DEBUG: Sending payment with quoteId: ${primaryQuoteId}, fileName: ${primaryFileName}`);
      console.log(`DEBUG: Technology: ${technology}, material: ${material}, quantity: ${firstItem.quantity}`);
      
      const piResponse = await createPaymentIntent({
        items: orderItems,
        currency: 'usd',
        customer_email: email, 
        metadata: { 
            customerName: name,
            cartItemIds: JSON.stringify(items.map(i => i.id)),
            quoteIds: JSON.stringify(quoteIds), // Add quote IDs to metadata
            
            // Add individual item metadata for easier webhook access
            quote_id: primaryQuoteId,  // This is critical - Stripe webhook looks for "quote_id"
            file_name: primaryFileName, // This is critical - Stripe webhook looks for "file_name"
            
            // Add detailed information
            technology: technology,
            material: material,
            quantity: String(firstItem.quantity || 1),
            
            // Add shipping cost metadata
            shipping_cost: String(shippingCost || 0),
            
            // Add a description that includes all key info for fallback
            description: `Quote ${primaryQuoteId} - ${primaryFileName} - ${technology} ${material}`
         },
        couponCode: couponCode || undefined  // Only include if provided
      });
      
      // Update UI if discount was applied
      if (piResponse.discount) {
        setDiscount(piResponse.discount);
        setDiscountedAmount(totalAmount * (1 - piResponse.discount / 100));
      }
      
      // Set test mode flag for UI feedback
      if (piResponse.isTestMode) {
        setIsTestMode(true);
      }

      if (piResponse.error || !piResponse.clientSecret) {
        throw new Error(piResponse.error || 'Failed to initialize payment.');
      }

      const { error: confirmError, paymentIntent } = await stripe.confirmCardPayment(
        piResponse.clientSecret,
        {
          payment_method: {
            card: cardElement,
            billing_details: {
              name: name,
              email: email,
            },
          },
        }
      );

      if (confirmError) {
        throw new Error(confirmError.message || 'Payment confirmation failed.');
      }

      if (paymentIntent?.status === 'succeeded') {
        console.log('PaymentIntent succeeded:', paymentIntent);
        console.log('Payment succeeded with quotes:', JSON.stringify(quoteIds));
        onPaymentSuccess(paymentIntent.id);
        
        // Prepare items info to pass to success page
        const itemsData = items.map(item => ({
          id: item.id,
          name: item.fileName,
          price: item.price,
          quantity: item.quantity,
          material: item.material,
          process: item.process,
          technology: item.technology || item.process,
        }));
        
        // Calculate rounded total amount for consistency
        const roundedTotalAmount = parseFloat(totalAmount.toFixed(2));
        
        // Create order data object
        const orderData = {
          paymentIntentId: paymentIntent.id,
          customerName: name,
          customerEmail: email,
          totalAmount: roundedTotalAmount,
          items: itemsData,
          timestamp: new Date().toISOString()
        };
        
        try {
          // Store the order data
          const storeResult = await fetch(`/api/order-data/${paymentIntent.id}`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json'
            },
            body: JSON.stringify(orderData)
          });
          
          if (!storeResult.ok) {
            console.error('Failed to store order data:', await storeResult.text());
          } else {
            console.log('Order data saved successfully');
          }
        } catch (storeError) {
          console.error('Error storing order data:', storeError);
        }

        // Redirect to the order success page
        const successUrl = `/order/success?payment_intent_id=${paymentIntent.id}`;
        window.location.href = successUrl;
        
        clearCart(); 
      } else {
        console.warn('PaymentIntent status:', paymentIntent?.status);
        throw new Error(`Payment processing resulted in status: ${paymentIntent?.status || 'unknown'}`);
      }

    } catch (error) {
      console.error('Payment processing error:', error);
      const message = error instanceof Error ? error.message : 'An unknown payment error occurred.';
      setErrorMessage(message);
      onPaymentError(message);
    } finally {
      onLoadingChange(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
       <div className="space-y-4">
         <div>
            <label htmlFor="name" className="block text-sm font-medium text-white/70 font-avenir mb-1">Full Name</label>
            <input
              id="name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              className="w-full bg-[#0A1525] border border-[#1E2A45] p-2 rounded-none text-white font-avenir text-sm focus:ring-[#5fe496] focus:border-[#5fe496] outline-none"
              placeholder="Jane Doe"
            />
          </div>
         <div>
            <label htmlFor="email" className="block text-sm font-medium text-white/70 font-avenir mb-1">Email</label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="w-full bg-[#0A1525] border border-[#1E2A45] p-2 rounded-none text-white font-avenir text-sm focus:ring-[#5fe496] focus:border-[#5fe496] outline-none"
              placeholder="jane.doe@example.com"
            />
          </div>
       </div>

      <div>
        <label htmlFor="couponCode" className="block text-sm font-medium text-white/70 font-avenir mb-1">Coupon Code (Optional)</label>
        <input
          id="couponCode"
          type="text"
          value={couponCode}
          onChange={(e) => setCouponCode(e.target.value.trim())}
          className="w-full bg-[#0A1525] border border-[#1E2A45] p-2 rounded-none text-white font-avenir text-sm focus:ring-[#5fe496] focus:border-[#5fe496] outline-none"
          placeholder="Enter coupon or test code"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-white/70 font-avenir mb-1">Card Details</label>
        <div className="bg-[#0A1525] border border-[#1E2A45] p-3 rounded-none">
          <CardElement options={cardElementOptions} />
        </div>
      </div>
      
      {/* Show discount message if applied */}
      {discount > 0 && (
        <div className="text-sm text-[#5fe496] font-avenir">
          Discount applied: {discount}% off
        </div>
      )}
      
      {/* Show test mode message */}
      {isTestMode && (
        <div className="text-sm text-[#F46036] font-avenir">
          Test mode active - no actual charge will be processed
        </div>
      )}

      {errorMessage && (
        <div className="text-sm text-[#F46036] font-avenir">
          {errorMessage}
        </div>
      )}

      <div className="pt-2">
        <GlowButton
          type="submit"
          disabled={!stripe || !elements}
          className="w-full bg-[#5fe496] text-[#0A1525] hover:bg-[#F46036] hover:text-white disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Pay ${discount > 0 ? discountedAmount.toFixed(2) : totalAmount.toFixed(2)}
        </GlowButton>
      </div>
    </form>
  );
}
