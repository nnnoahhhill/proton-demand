"use client";

import React, { useState } from 'react';
import { useCart } from '@/lib/cart';
import { createCheckoutSession } from '@/lib/api';
import { GlowButton } from '@/components/ui/glow-button';
import Link from 'next/link';
import { Trash2, Plus, Minus } from 'lucide-react';
import { loadStripe } from '@stripe/stripe-js';
import { Spinner } from "@/components/ui/spinner";

// Initialize Stripe outside the component rendering cycle
const stripePromise = process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY
  ? loadStripe(process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY)
  : null;

export default function CartPage() {
  const { items, removeItem, updateQuantity, totalItems, subtotalPrice, shippingCost, totalPrice } = useCart();
  const [isCheckingOut, setIsCheckingOut] = useState(false);
  const [checkoutError, setCheckoutError] = useState('');

  // Calculate total
  const subtotal = items.reduce((sum, item) => sum + item.price * item.quantity, 0);
  
  // Calculate shipping based on item weights - this is now just for logging
  const calculateShipping = () => {
    if (!items || items.length === 0) return 0;
    
    // Log shipping calculation start
    console.log(`\n
💲 CALCULATING SHIPPING COSTS (FOR DEBUGGING) 💲
Cart has ${items.length} items
`);
    
    // Add $10 base fee if cart is not empty
    const baseShippingFee = 10;
    
    // Calculate weight-based shipping
    const weightBasedShippingCost = items.reduce((total, item) => {
      if (!item) return total;
      
      // Get weight in kg
      const weightInKg = item.weightInKg || 0.1; // Default to 100g
      
      // Log each item's shipping contribution
      console.log(`Item: ${item.fileName}, Weight: ${weightInKg.toFixed(3)}kg, Quantity: ${item.quantity}, Shipping Contribution: $${(weightInKg * item.quantity * 20).toFixed(2)}`);
      
      // $20/kg shipping
      return total + (weightInKg * item.quantity * 20);
    }, 0);
    
    // Minimum $5 shipping overall
    return Math.max(5, baseShippingFee + weightBasedShippingCost);
  };
  
  // Calculate locally just for comparison/debugging
  const localShipping = calculateShipping();
  
  // Actually USE the shipping cost from cart context for consistency
  const shipping = shippingCost;
  
  // Log comparison for debugging
  console.log(`\n
🚚 SHIPPING COST COMPARISON 🚚
Local calculation (page.tsx): $${localShipping.toFixed(2)}
Cart context calculation: $${shipping.toFixed(2)} (USED)
`);
  
  const total = subtotal + shipping;

  const handleProceedToCheckout = async () => {
    if (!items || items.length === 0 || !stripePromise) {
      console.error('Checkout prerequisites not met:', { items, stripePromise });
      setCheckoutError(
        !stripePromise
          ? 'Stripe is not configured correctly.'
          : 'Your cart is empty.'
      );
      return;
    }

    setIsCheckingOut(true);
    setCheckoutError('');
    
    try {
      // CRITICAL TERMINAL LOGGING - Print all values to terminal
      console.log('\n===== CRITICAL CHECKOUT VALUES =====');
      console.log('CART ITEMS COUNT:', items.length);
      console.log('SUBTOTAL:', subtotal.toFixed(2));
      console.log('SHIPPING:', shipping.toFixed(2));
      console.log('TOTAL (SUBTOTAL + SHIPPING):', (subtotal + shipping).toFixed(2));
      
      // Log individual items for debugging
      if (items.length > 0) {
        console.log('\n----- Item Details -----');
        items.forEach((item, index) => {
          console.log(`ITEM ${index + 1}: ${item.fileName}`);
          console.log(`  Price: $${item.price.toFixed(2)}`);
          console.log(`  Quantity: ${item.quantity}`);
          console.log(`  Weight: ${item.weightInKg.toFixed(3)}kg`);
          console.log(`  Total Item Price: $${(item.price * item.quantity).toFixed(2)}`);
          console.log(`  Shipping Contribution: $${(item.weightInKg * item.quantity * 20).toFixed(2)}`);
        });
      }
      
      // Create a descriptive name for the order including total price with shipping
      const formattedTotal = (subtotal + shipping).toFixed(2);
      const orderName = items.length === 1
        ? `Quote ${items[0].id.substring(0, 8)} - ${items[0].fileName} - $${formattedTotal}`
        : `Order with ${items.length} items - Total $${formattedTotal} (incl. $${shipping.toFixed(2)} shipping)`;
      
      // Format items for the API
      const checkoutItems = items.map(item => ({
        id: item.id,
        name: item.fileName,
        price: item.price,
        quantity: item.quantity,
        description: `${item.process} - ${item.material}`
      }));
      
      // Use the shipping value from cart context
      const finalShippingCost = shipping;
      
      console.log('\n===== CHECKOUT SUMMARY =====');
      console.log('ORDER NAME:', orderName);
      console.log('ITEMS:', checkoutItems.length);
      console.log('SUBTOTAL:', subtotal.toFixed(2));
      console.log('SHIPPING:', finalShippingCost.toFixed(2));
      console.log('TOTAL:', (subtotal + finalShippingCost).toFixed(2));
      
      // Create checkout session
      const checkoutResponse = await createCheckoutSession({
        item_name: orderName,
        price: subtotal + finalShippingCost,  // Total price without shipping
        currency: items[0].currency || 'usd',
        // Use the new items array parameter
        items: checkoutItems,
        // Add fallback quote_id and file_name for backward compatibility with the backend
        quote_id: items.length === 1 ? items[0].id : items.map(item => item.id).join(','),
        file_name: items.length === 1 ? items[0].fileName : 'Multiple Files',
        shipping_cost: finalShippingCost // Use the shipping cost displayed in the UI
      });
      
      // Log response success/failure
      console.log('CHECKOUT API:', checkoutResponse.error ? 'ERROR' : 'SUCCESS');

      if (checkoutResponse.error || !checkoutResponse.sessionId) {
        const errorMsg = checkoutResponse.error || 'Failed to initiate payment session. Please try again.';
        console.error("Checkout session creation failed:", errorMsg);
        setCheckoutError(errorMsg);
        setIsCheckingOut(false);
        return;
      }
      
      const stripe = await stripePromise;
      if (!stripe) {
        console.error('Stripe.js failed to load.');
        setCheckoutError('Payment gateway failed to load. Please try again.');
        setIsCheckingOut(false);
        return;
      }
      
      console.log("Redirecting to Stripe checkout...");

      const { error } = await stripe.redirectToCheckout({
        sessionId: checkoutResponse.sessionId,
      });

      if (error) {
        console.error('Stripe redirect error:', error);
        // Provide a more descriptive error message based on the error type
        const errorMessage = error.message || 'Failed to redirect to payment page.';
        setCheckoutError(errorMessage);
        setIsCheckingOut(false);
      }
    } catch (err) {
      console.error('Error during checkout process:', err);
      // Provide more specific error messages based on the error type
      let errorMessage = 'An unknown error occurred during checkout.';
      
      if (err instanceof Error) {
        errorMessage = err.message;
        // Handle network errors specifically
        if (err.message.includes('network') || err.message.includes('fetch')) {
          errorMessage = 'Network error. Please check your internet connection and try again.';
        }
      }
      
      setCheckoutError(errorMessage);
      setIsCheckingOut(false);
    }
  };

  // Auto-dismiss error
  React.useEffect(() => {
    if (checkoutError) {
      const timer = setTimeout(() => setCheckoutError(''), 6000);
      return () => clearTimeout(timer);
    }
  }, [checkoutError]);

  if (items.length === 0 && !isCheckingOut) {
    return (
      <div className="container mx-auto px-4 py-8 text-center font-avenir">
        <h1 className="text-3xl font-andale mb-6 text-white">Your Cart is Empty</h1>
        <p className="text-white/70 mb-8">Looks like you haven't added any quotes yet.</p>
        <Link href="/quote">
            <GlowButton className="bg-[#1e87d6] text-white hover:bg-[#1e87d6]/80">
              Get a Quote
            </GlowButton>
        </Link>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8 font-avenir text-white relative">
       {/* Loading overlay */}
       {isCheckingOut && (
        <div className="absolute inset-0 bg-[#0A1525]/80 backdrop-blur-sm z-10 flex flex-col items-center justify-center">
          <Spinner size={120} />
            <p className="mt-6 text-xl text-white font-andale">Redirecting to secure payment...</p>
            <p className="mt-2 text-white/70 font-avenir">Please wait</p>
            {checkoutError && <p className="mt-4 text-red-400 font-semibold">Error: {checkoutError}</p>}
        </div>
      )}

      {/* Checkout Error Popup */}
      {checkoutError && !isCheckingOut && (
          <div className="absolute top-1/4 left-1/2 transform -translate-x-1/2 z-20 p-4 border border-[#F46036] bg-[#0A1525] text-[#F46036] font-avenir shadow-lg max-w-md opacity-90 hover:opacity-100">
            <div className="flex justify-between items-start">
              <div>Error: {checkoutError}</div>
              <button onClick={() => setCheckoutError('')} className="ml-4 text-white/70 hover:text-white">×</button>
            </div>
          </div>
        )}

      <h1 className="text-3xl font-andale mb-8 text-white">Your Cart</h1>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Cart Items List */}
        <div className="lg:col-span-2 space-y-4">
          {items.map((item) => (
            <div key={item.id} className="flex items-start justify-between bg-[#0C1F3D]/60 border border-[#1E2A45] p-4 rounded-none">
              <div className="flex-grow mr-4">
                <p className="font-semibold text-lg">Quote: {item.id}</p>
                <p className="text-sm text-white/80">File: {item.fileName}</p>
                <p className="text-sm text-white/70">Process: {item.process}</p>
                <p className="text-sm text-white/70">Material: {item.material}</p>
              </div>
              <div className="flex items-center space-x-2 ml-4 flex-shrink-0">
                 <button
                    onClick={() => updateQuantity(item.id, Math.max(1, item.quantity - 1))}
                    className="p-1 border border-[#1E2A45] bg-[#0A1525] hover:bg-[#1E2A45] disabled:opacity-50 disabled:cursor-not-allowed"
                    disabled={item.quantity <= 1}
                 >
                     <Minus size={16} />
                 </button>
                 <span className="text-lg w-10 text-center font-mono select-none">{item.quantity}</span>
                 <button
                    onClick={() => updateQuantity(item.id, item.quantity + 1)}
                    className="p-1 border border-[#1E2A45] bg-[#0A1525] hover:bg-[#1E2A45]"
                  >
                     <Plus size={16} />
                 </button>
                <span className="text-lg w-24 text-right ml-4">${item.price.toFixed(2)} {item.currency}</span>
                <button onClick={() => removeItem(item.id)} className="text-red-500 hover:text-red-400 ml-2">
                  <Trash2 size={20} />
                </button>
              </div>
            </div>
          ))}
        </div>

        {/* Order Summary */}
        <div className="lg:col-span-1 bg-[#0C1F3D]/60 border border-[#1E2A45] p-6 rounded-none h-fit">
          <h2 className="text-2xl font-andale mb-6">Order Summary</h2>
          <div className="space-y-3 mb-6">
            <div className="flex justify-between">
              <span>Subtotal ({totalItems} items)</span>
              <span>${subtotal.toFixed(2)}</span>
            </div>
            <div className="flex justify-between">
              <span>Shipping</span>
              <span>${shipping.toFixed(2)}</span>
            </div>
            <hr className="border-t border-[#1E2A45] my-2" />
            <div className="flex justify-between font-bold text-xl">
              <span>Total</span>
              <span>${total.toFixed(2)}</span>
            </div>
          </div>
          <GlowButton
            onClick={handleProceedToCheckout}
            className="w-full bg-[#5fe496] text-[#0A1525] hover:bg-[#5fe496]/80"
            disabled={isCheckingOut || items.length === 0}
          >
            {isCheckingOut ? 'Processing...' : 'Proceed to Checkout'}
          </GlowButton>
          {(!stripePromise || checkoutError) && (
            <p className="text-xs text-center mt-2 text-red-400">
              {!stripePromise ? "Stripe not configured." : checkoutError ? "Checkout Error. See console/popup." : "Checkout requires backend endpoint." }
            </p>
          )}
        </div>
      </div>
    </div>
  );
} 