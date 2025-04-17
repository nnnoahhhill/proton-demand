import { NextRequest, NextResponse } from 'next/server';
import Stripe from 'stripe';
import { CartItem } from '@/lib/cart';

// Configure Stripe based on environment
const getStripeInstance = (isTestMode: boolean = false) => {
  let stripeKey: string;
  
  if (process.env.NODE_ENV === 'production' && !isTestMode) {
    // Use production key for real transactions
    stripeKey = process.env.STRIPE_LIVE_SECRET_KEY || '';
  } else {
    // Use test key for development or test/coupon orders
    stripeKey = process.env.STRIPE_TEST_SECRET_KEY || '';
  }
  
  return new Stripe(stripeKey, {
    apiVersion: '2023-10-16', // Use the latest API version
  });
};

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();

    // Extract data from the request
    const {
      items,
      customerEmail,
      customerName,
      shippingAddress,
      specialInstructions,
      metadata = {},
      couponCode
    } = body;

    if (!items || !items.length) {
      return NextResponse.json(
        { error: 'No items provided' },
        { status: 400 }
      );
    }

    // Calculate the total amount
    const amount = items.reduce(
      (total: number, item: CartItem) => total + (item.price * item.quantity),
      0
    );

    // Add shipping cost ($20/kg)
    const shippingCost = items.reduce(
      (total: number, item: CartItem) =>
        total + (item.weightInKg * item.quantity * 20),
      0
    );

    let totalAmount = Math.round((amount + shippingCost) * 100); // Convert to cents

    // Check if admin/test coupon code is provided
    let isTestMode = false;
    let discountPercent = 0;
    
    if (couponCode) {
      // Check against valid admin codes - in production, these should be stored securely
      // Here are some examples of test mode codes
      const validTestCodes: Record<string, number> = {
        'ADMINTEST': 100, // 100% discount
        'TEST50OFF': 50,  // 50% discount
        'PROTONDEV': 100  // 100% discount
      };
      
      if (couponCode in validTestCodes) {
        discountPercent = validTestCodes[couponCode];
        
        // Apply discount
        totalAmount = Math.round(totalAmount * (1 - discountPercent / 100));
        isTestMode = true;
        
        // If 100% discount, set to a minimal amount (Stripe requires min 1 cent)
        if (totalAmount === 0) {
          totalAmount = 1; // 1 cent
        }

        console.log(`Test code ${couponCode} applied: ${discountPercent}% discount`);
      }
    }

    // Get appropriate Stripe instance based on mode
    const stripe = getStripeInstance(isTestMode);

    // Create a payment intent
    const paymentIntent = await stripe.paymentIntents.create({
      amount: totalAmount,
      currency: 'usd',
      payment_method_types: ['card'],
      description: `Order for ${customerName}`,
      receipt_email: customerEmail,
      shipping: {
        name: customerName,
        address: {
          line1: shippingAddress.line1,
          line2: shippingAddress.line2 || '',
          city: shippingAddress.city,
          state: shippingAddress.state,
          postal_code: shippingAddress.postal_code,
          country: shippingAddress.country,
        },
      },
      metadata: {
        customerEmail,
        customerName,
        itemCount: items.length.toString(),
        specialInstructions: specialInstructions || '',
        isTestMode: isTestMode.toString(), // Record if this was a test order
        couponCode: couponCode || '',      // Record coupon code if used
        ...metadata,
      },
    });

    return NextResponse.json({
      clientSecret: paymentIntent.client_secret,
      paymentIntentId: paymentIntent.id,
      amount: totalAmount / 100, // Convert back to dollars
      currency: paymentIntent.currency,
      isTestMode,                // Return flag for UI feedback
      discount: discountPercent, // Return discount percentage for UI feedback
    });
  } catch (error) {
    console.error('Error creating payment intent:', error);

    return NextResponse.json(
      {
        error: error instanceof Error ? error.message : 'Unknown error occurred'
      },
      { status: 500 }
    );
  }
}
