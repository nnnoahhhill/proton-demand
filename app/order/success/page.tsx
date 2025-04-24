"use client";

import React, { useEffect, useState, Suspense } from 'react';
import Link from 'next/link';
import { useCart } from '@/lib/cart';
import { GlowButton } from '@/components/ui/glow-button';
import { CheckCircle } from 'lucide-react';
import { useSearchParams } from 'next/navigation'; // To read query params
import { Spinner } from "@/components/ui/spinner";

// Material display name mapping
function getMaterialDisplayName(materialId: string): string {
  const materialMappings: Record<string, string> = {
    'sla_resin_standard': 'Standard Resin',
    'PLA': 'PLA',
    'ABS': 'ABS',
    'PETG': 'PETG',
    'TPU': 'TPU',
    'NYLON_12': 'Nylon 12',
    'ASA': 'ASA',
    'NYLON_12_WHITE': 'Nylon 12 (White)',
    'NYLON_12_BLACK': 'Nylon 12 (Black)',
    'STANDARD_RESIN': 'Standard Resin',
    'ALUMINUM_6061': 'Aluminum 6061',
    'MILD_STEEL': 'Mild Steel',
    'STAINLESS_STEEL_304': 'Stainless Steel 304',
    'STAINLESS_STEEL_316': 'Stainless Steel 316',
    'TITANIUM': 'Titanium',
    'COPPER': 'Copper',
    'BRASS': 'Brass',
    'SLA': 'SLA 3D Printing',
    'FDM': 'FDM 3D Printing',
    'SLS': 'SLS 3D Printing',
  };
  
  return materialMappings[materialId] || materialId;
}

// Define the type for order data
interface OrderItem {
  id: string;
  name: string;
  fileName?: string;
  price: number;
  quantity: number;
  material: string;
  process?: string;
  technology?: string;
}

interface OrderData {
  paymentIntentId: string;
  customerName: string;
  customerEmail: string;
  totalAmount: number;
  items: OrderItem[];
  timestamp: string;
}

// Component that uses useSearchParams - must be wrapped in Suspense
function OrderDetails() {
  const { clearCart, isInitialized } = useCart();
  const searchParams = useSearchParams();
  const [isLoading, setIsLoading] = useState(true);
  const [orderData, setOrderData] = useState<OrderData | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  
  // Check for multiple possible URL parameters for the order ID
  // 1. Payment intent from our own checkout form: payment_intent_id, payment_intent 
  // 2. Stripe checkout session ID: session_id
  const paymentIntentId = searchParams.get('payment_intent_id') || searchParams.get('payment_intent');
  const sessionId = searchParams.get('session_id');
  
  // Stripe checkout returns a session ID, but we need to use that directly
  // Our backend now stores JSON files with both payment intent ID and session ID
  const orderId = sessionId || paymentIntentId;
  
  // For debugging
  console.log("Success page parameters:", {
    paymentIntentId,
    sessionId,
    orderId
  });

  // Fetch order data from our API
  useEffect(() => {
    if (orderId) {
      setIsLoading(true);
      
      console.log("Fetching order data for:", orderId);
      
      // Try to fetch the order data
      const fetchOrderData = async () => {
        try {
          // The session ID will work directly now because our backend stores
          // the order data with both the session ID and the payment intent ID
          const res = await fetch(`/api/order-data/${orderId}`);
          console.log("Order data fetch status:", res.status);
          
          // Continue with original response handling
          const data = await res.json();
          
          if (data.success) {
            console.log("Order data loaded successfully:", data.order);
            setOrderData(data.order);
          } else {
            console.error("Error loading order data:", data.error);
            setLoadError(data.error || "Failed to load order data");
            
            // If it's a 404, the order data may not have been stored yet
            // This can happen if Stripe redirects before the webhook was processed
            if (data.error === "Order data not found" && sessionId) {
              console.log("Session ID present, order data may be pending webhook processing");
            }
          }
        } catch (err) {
          console.error("Error fetching order data:", err);
          setLoadError("Failed to fetch order details");
        } finally {
          setIsLoading(false);
        }
      };
      
      fetchOrderData();
    } else {
      console.error("No order ID provided in URL parameters");
      setIsLoading(false);
      setLoadError("No order ID provided");
    }
  }, [orderId, sessionId]);

  // Clear the cart once the component mounts AND cart is initialized
  useEffect(() => {
    if (isInitialized) { // Only clear if context is ready
      console.log("OrderSuccessPage: Cart is initialized, clearing cart.");
      clearCart(true); // Pass true to indicate this is a successful order
    }
  }, [clearCart, isInitialized]); // Add isInitialized dependency

  return (
    <>
      {isLoading ? (
        <div className="flex flex-col justify-center items-center py-12">
          <Spinner className="h-8 w-8 text-[#5fe496] mb-4" />
          <p className="text-white/80 mb-2">Loading order details...</p>
          <p className="text-white/60 text-sm max-w-md text-center">
            This may take a moment as we process your order details. Your payment has been confirmed.
          </p>
          {orderId && <p className="text-white/60 text-xs mt-4">Order ID: {orderId}</p>}
        </div>
      ) : loadError ? (
          <div className="mb-4">
            <h2 className="text-lg font-semibold text-[#5fe496] mb-1">Order Details</h2>
            <p className="text-white">Order ID: <span className="text-[#5fe496] font-mono">{orderId || "Unknown"}</span></p>
          </div>
      ) : (
        <div className="max-w-2xl mx-auto border border-[#1E2A45] bg-[#0A1525]/50 p-6 mb-8 text-left">
          {/* Order Details - Always show this section */}
          <div className="mb-4">
            <h2 className="text-lg font-semibold text-[#5fe496] mb-1">Order Details</h2>
            <p className="text-white">Order ID: <span className="text-[#5fe496] font-mono">{orderData?.paymentIntentId || orderId || "Processing..."}</span></p>
            {orderData?.totalAmount && (
              <p className="text-white">Total: ${orderData.totalAmount.toFixed(2)} USD</p>
            )}
            {orderData?.timestamp && (
              <p className="text-white/70 text-sm">
                Order Date: {new Date(orderData.timestamp).toLocaleString()}
              </p>
            )}
          </div>
          
          {/* Customer Info */}
          {(orderData?.customerName || orderData?.customerEmail) && (
            <div className="mb-4">
              <h2 className="text-lg font-semibold text-[#5fe496] mb-1">Customer Information</h2>
              {orderData.customerName && <p className="text-white">Name: {orderData.customerName}</p>}
              {orderData.customerEmail && <p className="text-white">Email: {orderData.customerEmail}</p>}
            </div>
          )}
          
          {/* Items */}
          <div className="mb-4">
            <h2 className="text-lg font-semibold text-[#5fe496] mb-1">Ordered Parts</h2>
            {orderData?.items && orderData.items.length > 0 ? (
              <ul className="space-y-2">
                {orderData.items.map((item, index) => (
                  <li key={index} className="border-b border-[#1E2A45] pb-2">
                    <p className="text-white font-medium">
                      <strong className="text-[#5fe496]">{index + 1}.</strong> {item.fileName || item.name}
                    </p>
                    <p className="text-sm text-white/80">
                      • <strong>QUANTITY:</strong> {item.quantity}
                    </p>
                    <p className="text-sm text-white/80">
                      • <strong>Technology:</strong> {getMaterialDisplayName(item.technology || item.process || "Standard")}
                    </p>
                    <p className="text-sm text-white/80">
                      • <strong>Material:</strong> <span className="text-[#5fe496]">{getMaterialDisplayName(item.material || "Default")}</span>
                    </p>
                    <p className="text-sm text-white/80">
                      • Quote ID: <span className="text-[#5fe496]">{item.id}</span>
                    </p>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-white/70">Order details will be sent in your confirmation email</p>
            )}
          </div>
          
          <p className="text-sm text-white/70 mt-4">
            Keep these references for future communications
          </p>
        </div>
      )}
    </>
  );
}

export default function OrderSuccessPage() {
  return (
    <div className="container mx-auto px-4 py-16 text-center font-avenir text-white">
      <CheckCircle className="mx-auto h-24 w-24 text-green-500 mb-6" />
      <h1 className="text-4xl font-andale mb-4 text-white">Order Successful!</h1>
      <p className="text-white/80 mb-4 text-lg">Thank you for your purchase.</p>
      
      <Suspense fallback={
        <div className="flex flex-col justify-center items-center py-12">
          <Spinner className="h-8 w-8 text-[#5fe496] mb-4" />
          <p className="text-white/80 mb-2">Loading order details...</p>
        </div>
      }>
        <OrderDetails />
      </Suspense>
      
      <p className="text-white/70 mb-8">
        You will receive an order confirmation email shortly.
      </p>
      
      <div className="flex flex-col sm:flex-row justify-center gap-4">
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