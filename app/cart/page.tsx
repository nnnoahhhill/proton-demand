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

    // For simplicity, we'll checkout the first item only for now.
    // TODO: Modify backend to handle multiple items or iterate here.
    const firstItem = items[0];

    try {
      const checkoutResponse = await createCheckoutSession({
        // Using the first item's details
        item_name: `Quote ${firstItem.id.substring(0, 8)} - ${firstItem.fileName}`,
        price: firstItem.price, // Price per unit
        currency: firstItem.currency || 'usd',
        quantity: firstItem.quantity,
        quote_id: firstItem.id,
        file_name: firstItem.fileName
      });

      if (checkoutResponse.error || !checkoutResponse.sessionId) {
        console.error("Failed to create checkout session:", checkoutResponse.error);
        setCheckoutError(checkoutResponse.error || 'Failed to initiate payment session. Backend endpoint might be missing or returning an error.');
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

      const { error } = await stripe.redirectToCheckout({
        sessionId: checkoutResponse.sessionId,
      });

      if (error) {
        console.error('Stripe redirect error:', error);
        setCheckoutError(error.message || 'Failed to redirect to payment page.');
        // Don't set isCheckingOut to false if redirect fails, user might retry
      }
    } catch (err) {
      console.error('Error during checkout process:', err);
      setCheckoutError(err instanceof Error ? err.message : 'An unknown error occurred during checkout.');
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
              <span>${subtotalPrice.toFixed(2)}</span>
            </div>
            <div className="flex justify-between">
              <span>Est. Shipping</span>
              <span>${shippingCost.toFixed(2)}</span>
            </div>
            <hr className="border-t border-[#1E2A45] my-2" />
            <div className="flex justify-between font-bold text-xl">
              <span>Total</span>
              <span>${totalPrice.toFixed(2)}</span>
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