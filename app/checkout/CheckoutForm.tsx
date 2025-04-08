"use client";

import { useState } from 'react';
import { useStripe, useElements, CardElement } from '@stripe/react-stripe-js';
import { useRouter } from 'next/navigation';
import { GlowButton } from '@/components/ui/glow-button';
import { createPaymentIntent } from '@/lib/stripe';
import { useCart, CartItem } from '@/lib/cart';
import { sendOrderNotification } from '@/lib/slack';

interface CheckoutFormProps {
  items: CartItem[];
  totalPrice: number;
  subtotalPrice: number;
  shippingCost: number;
  formData: {
    fullName: string;
    email: string;
    phone: string;
    address: string;
    city: string;
    state: string;
    zipCode: string;
    country: string;
    specialInstructions?: string;
  };
  onPrevStep: () => void;
}

export default function CheckoutForm({ 
  items, 
  totalPrice, 
  subtotalPrice,
  shippingCost,
  formData, 
  onPrevStep 
}: CheckoutFormProps) {
  const stripe = useStripe();
  const elements = useElements();
  const router = useRouter();
  const { clearCart } = useCart();
  const [isProcessing, setIsProcessing] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!stripe || !elements) {
      // Stripe.js has not loaded yet
      return;
    }
    
    setIsProcessing(true);
    setErrorMessage('');
    
    try {
      // Create a payment intent
      const paymentIntentResponse = await createPaymentIntent({
        items,
        customerEmail: formData.email,
        customerName: formData.fullName,
        shippingAddress: {
          line1: formData.address,
          city: formData.city,
          state: formData.state,
          postal_code: formData.zipCode,
          country: formData.country,
        },
        specialInstructions: formData.specialInstructions,
        metadata: {
          orderType: 'manufacturing',
          phone: formData.phone,
        },
      });
      
      // Confirm the payment
      const cardElement = elements.getElement(CardElement);
      if (!cardElement) {
        throw new Error('Card element not found');
      }
      
      const { error, paymentIntent } = await stripe.confirmCardPayment(
        paymentIntentResponse.clientSecret,
        {
          payment_method: {
            card: cardElement,
            billing_details: {
              name: formData.fullName,
              email: formData.email,
              phone: formData.phone,
              address: {
                line1: formData.address,
                city: formData.city,
                state: formData.state,
                postal_code: formData.zipCode,
                country: formData.country,
              }
            },
          },
        }
      );
      
      if (error) {
        throw new Error(error.message);
      }
      
      if (paymentIntent.status === 'succeeded') {
        // Payment successful
        
        // Get model files from items
        const modelFiles = items.map(item => {
          // In a real implementation, you would retrieve the actual files
          // For now, we'll just use placeholder data
          return new File(
            [new Blob(['placeholder'])], 
            item.fileName, 
            { type: 'application/octet-stream' }
          );
        });
        
        // Send order notification to Slack
        await sendOrderNotification({
          orderId: paymentIntentResponse.paymentIntentId,
          customerName: formData.fullName,
          customerEmail: formData.email,
          items: items.map(item => ({
            id: item.id,
            fileName: item.fileName,
            process: item.process,
            material: item.material,
            finish: item.finish,
            quantity: item.quantity,
            price: item.price,
          })),
          totalPrice,
          currency: 'usd',
          specialInstructions: formData.specialInstructions,
          shippingAddress: {
            line1: formData.address,
            city: formData.city,
            state: formData.state,
            postal_code: formData.zipCode,
            country: formData.country,
          },
          files: modelFiles,
        });
        
        // Clear the cart and redirect to success page
        clearCart();
        router.push('/checkout/success');
      }
    } catch (error) {
      console.error('Payment error:', error);
      setErrorMessage(error instanceof Error ? error.message : 'An error occurred during payment processing');
    } finally {
      setIsProcessing(false);
    }
  };
  
  const cardElementOptions = {
    style: {
      base: {
        fontSize: '16px',
        color: '#FFFFFF',
        '::placeholder': {
          color: 'rgba(255, 255, 255, 0.5)',
        },
        iconColor: '#FFFFFF',
      },
      invalid: {
        color: '#F46036',
        iconColor: '#F46036',
      },
    },
    hidePostalCode: true,
  };
  
  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <div className="mb-6">
        <h3 className="text-xl font-andale mb-4 text-white">Payment Information</h3>
        
        <div className="space-y-4">
          <div>
            <label className="block text-white/70 mb-2 font-avenir">Card Details</label>
            <div className="bg-[#0A1525] border border-[#1E2A45] p-3 rounded-none">
              <CardElement options={cardElementOptions} />
            </div>
          </div>
        </div>
      </div>
      
      {errorMessage && (
        <div className="p-4 border border-[#F46036] bg-[#F46036]/10 text-[#F46036] mb-4 font-avenir">
          {errorMessage}
        </div>
      )}
      
      <div className="flex justify-between">
        <GlowButton
          type="button"
          onClick={onPrevStep}
          variant="outline"
        >
          Back
        </GlowButton>
        
        <GlowButton
          type="submit"
          disabled={isProcessing || !stripe}
          className="bg-[#F46036] text-white hover:bg-[#F46036]/80"
        >
          {isProcessing ? 'Processing...' : `Pay $${totalPrice.toFixed(2)}`}
        </GlowButton>
      </div>
    </form>
  );
}
