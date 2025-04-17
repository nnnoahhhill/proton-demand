"use client";

import React, { useEffect } from 'react';
import Link from 'next/link';
import { useCart } from '@/lib/cart';
import { GlowButton } from '@/components/ui/glow-button';
import { CheckCircle } from 'lucide-react';
import { useSearchParams } from 'next/navigation'; // To read query params

export default function OrderSuccessPage() {
  const { clearCart, isInitialized } = useCart();
  const searchParams = useSearchParams();
  const sessionId = searchParams.get('session_id');

  // Clear the cart once the component mounts AND cart is initialized
  useEffect(() => {
    if (isInitialized) { // Only clear if context is ready
        console.log("OrderSuccessPage: Cart is initialized, clearing cart.");
        clearCart();
    }
  }, [clearCart, isInitialized]); // Add isInitialized dependency

  return (
    <div className="container mx-auto px-4 py-16 text-center font-avenir text-white">
      <CheckCircle className="mx-auto h-24 w-24 text-green-500 mb-6" />
      <h1 className="text-4xl font-andale mb-4 text-white">Order Successful!</h1>
      <p className="text-white/80 mb-8 text-lg">Thank you for your purchase.</p>
      {sessionId && (
        <p className="text-sm text-white/60 mb-8">Your order reference (Session ID): {sessionId}</p>
      )}
      <p className="text-white/70 mb-8">
        You will receive an order confirmation email shortly.
      </p>
      <div className="flex justify-center space-x-4">
         <Link href="/quote">
            <GlowButton className="bg-[#1e87d6] text-white hover:bg-[#1e87d6]/80">
              Order Another Part
            </GlowButton>
        </Link>
        <Link href="/">
            <GlowButton className="bg-[#0C1F3D] border border-[#1E2A45] text-white hover:bg-[#1E2A45]">
              Back to Home
            </GlowButton>
        </Link>
      </div>
    </div>
  );
} 