import { NextRequest, NextResponse } from 'next/server';
import Stripe from 'stripe';
import { CartItem } from '@/lib/cart';

// Initialize Stripe with the secret key
const stripe = new Stripe(process.env.STRIPE_SECRET_KEY || '', {
  apiVersion: '2023-10-16', // Use the latest API version
});

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    
    // Extract data from the request
    const { 
      items, 
      customerEmail, 
      customerName, 
      shippingAddress, 
      metadata = {} 
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
    
    const totalAmount = Math.round((amount + shippingCost) * 100); // Convert to cents
    
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
        ...metadata,
      },
    });
    
    return NextResponse.json({
      clientSecret: paymentIntent.client_secret,
      paymentIntentId: paymentIntent.id,
      amount: totalAmount / 100, // Convert back to dollars
      currency: paymentIntent.currency,
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
