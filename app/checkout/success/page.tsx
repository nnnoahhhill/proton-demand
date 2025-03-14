"use client";

import Link from 'next/link';
import { GlowButton } from '@/components/ui/glow-button';

export default function CheckoutSuccessPage() {
  // Generate a random order number for demo purposes
  const orderNumber = `ORD-${Math.floor(Math.random() * 1000000).toString().padStart(6, '0')}`;
  
  // Calculate estimated delivery date (10 business days from now)
  const deliveryDate = getEstimatedDeliveryDate(10);
  
  return (
    <div className="container px-4 md:px-6 py-20">
      <div className="max-w-3xl mx-auto glow-card rounded-none border border-[#5fe496] bg-[#0C1F3D]/30 p-12 backdrop-blur-sm text-center">
        <div className="w-20 h-20 bg-[#5fe496]/10 rounded-full flex items-center justify-center mx-auto mb-8">
          <svg 
            xmlns="http://www.w3.org/2000/svg" 
            width="40" 
            height="40" 
            viewBox="0 0 24 24" 
            fill="none" 
            stroke="#5fe496" 
            strokeWidth="2" 
            strokeLinecap="round" 
            strokeLinejoin="round"
          >
            <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
            <polyline points="22 4 12 14.01 9 11.01"></polyline>
          </svg>
        </div>
        
        <h1 className="text-4xl font-andale text-[#5fe496] mb-4">Order Successful!</h1>
        
        <p className="text-xl text-white/70 mb-6 font-avenir">
          Thank you for your order. We've received your request and will begin processing it right away.
        </p>
        
        <div className="p-6 border border-[#1E2A45] bg-[#0A1525]/50 mb-6">
          <p className="text-white/70 font-avenir">Order Number</p>
          <p className="text-2xl font-andale text-white">{orderNumber}</p>
        </div>
        
        <div className="p-6 border border-[#F46036] bg-[#F46036]/10 mb-8">
          <p className="text-white/70 font-avenir mb-1">Estimated Delivery Date</p>
          <p className="text-xl font-andale text-[#F46036]">{deliveryDate}</p>
          <p className="text-sm text-white/70 mt-2 font-avenir">
            Your order will be delivered within 10 business days from today
          </p>
        </div>
        
        <p className="text-white/70 mb-8 font-avenir">
          A confirmation email with your order details has been sent to your email address.
          You can also track your order status on your account page.
        </p>
        
        <div className="flex flex-col sm:flex-row gap-4 justify-center">
          <GlowButton asChild>
            <Link href="/">Return to Home</Link>
          </GlowButton>
          
          <GlowButton asChild variant="outline">
            <Link href="/quote">Place Another Order</Link>
          </GlowButton>
        </div>
      </div>
    </div>
  );
}

// Helper function to calculate delivery date (skipping weekends)
function getEstimatedDeliveryDate(businessDays: number): string {
  const date = new Date();
  let daysToAdd = businessDays;
  
  while (daysToAdd > 0) {
    date.setDate(date.getDate() + 1);
    // Skip weekends (0 = Sunday, 6 = Saturday)
    if (date.getDay() !== 0 && date.getDay() !== 6) {
      daysToAdd--;
    }
  }
  
  // Format the date
  return date.toLocaleDateString('en-US', { 
    weekday: 'long',
    year: 'numeric', 
    month: 'long', 
    day: 'numeric'
  });
} 