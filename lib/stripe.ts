/**
 * Stripe integration service
 */
import { loadStripe, Stripe } from '@stripe/stripe-js';
import { CartItem } from './cart';

// Initialize Stripe with the public key
const stripePromise = loadStripe(process.env.NEXT_PUBLIC_STRIPE_PUBLIC_KEY || '');

/**
 * Interface for creating a payment intent
 */
export interface CreatePaymentIntentRequest {
  items: CartItem[];
  customerEmail: string;
  customerName: string;
  shippingAddress: {
    line1: string;
    line2?: string;
    city: string;
    state: string;
    postal_code: string;
    country: string;
  };
  specialInstructions?: string;
  metadata?: Record<string, string>;
}

/**
 * Interface for payment intent response
 */
export interface PaymentIntentResponse {
  clientSecret: string;
  paymentIntentId: string;
  amount: number;
  currency: string;
}

/**
 * Create a payment intent
 *
 * @param params Payment intent request parameters
 * @returns Payment intent response
 */
export async function createPaymentIntent(params: CreatePaymentIntentRequest): Promise<PaymentIntentResponse> {
  try {
    const response = await fetch('/api/create-payment-intent', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(params),
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || 'Failed to create payment intent');
    }

    return await response.json();
  } catch (error) {
    console.error('Error creating payment intent:', error);
    throw error;
  }
}

/**
 * Get the Stripe instance
 *
 * @returns Promise resolving to the Stripe instance
 */
export function getStripe(): Promise<Stripe | null> {
  return stripePromise;
}
