"use client";

import Link from 'next/link';
import { useCart } from '@/lib/cart';

export function CartIcon() {
  const { totalItems } = useCart();

  return (
    <Link href="/cart" className="relative inline-flex items-center">
      <svg 
        xmlns="http://www.w3.org/2000/svg" 
        width="24" 
        height="24" 
        viewBox="0 0 24 24" 
        fill="none" 
        stroke="currentColor" 
        strokeWidth="2" 
        strokeLinecap="round" 
        strokeLinejoin="round" 
        className="text-white hover:text-[#5fe496] transition-colors"
      >
        <circle cx="8" cy="21" r="1" />
        <circle cx="19" cy="21" r="1" />
        <path d="M2.05 2.05h2l2.66 12.42a2 2 0 0 0 2 1.58h9.78a2 2 0 0 0 1.95-1.57l1.65-7.43H5.12" />
      </svg>
      
      {totalItems > 0 && (
        <span className="absolute -top-2 -right-2 flex items-center justify-center w-5 h-5 rounded-full bg-[#F46036] text-white text-xs font-bold">
          {totalItems}
        </span>
      )}
    </Link>
  );
} 