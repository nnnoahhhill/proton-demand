/**
 * API route for storing and retrieving order data
 * Used by the checkout form to store order details after payment
 * Used by the order success page to display order details
 */
import { NextRequest, NextResponse } from 'next/server';
import { storeFileInBlob, getFileFromBlob, listFilesInBlob } from '@/lib/blob';
import path from 'path';

// GET handler - retrieve order data
export async function GET(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    // In NextJS 13+, params needs to be awaited
    const { id } = await Promise.resolve(params);
    
    // Make sure ID is valid to prevent security issues
    if (!id || id.includes('/') || id.includes('..')) {
      return NextResponse.json(
        { success: false, error: 'Invalid order ID' },
        { status: 400 }
      );
    }
    
    // Construct blob path
    const blobPath = `orders/${id}.json`;
    
    try {
      // List blobs to find this order
      const listResult = await listFilesInBlob(blobPath);
      
      if (listResult.length === 0) {
        return NextResponse.json(
          { success: false, error: 'Order data not found' },
          { status: 404 }
        );
      }
      
      // Get the blob URL and fetch it
      const blobUrl = listResult[0].url;
      const fileBuffer = await getFileFromBlob(blobUrl);
      
      if (!fileBuffer) {
        return NextResponse.json(
          { success: false, error: 'Order data not found' },
          { status: 404 }
        );
      }
      
      // Parse the order data
      const orderData = JSON.parse(fileBuffer.toString());
      
      return NextResponse.json({
        success: true,
        order: orderData
      });
    } catch (getError) {
      console.error('Error getting order data from blob storage:', getError);
      return NextResponse.json(
        { success: false, error: 'Order data not found' },
        { status: 404 }
      );
    }
  } catch (error) {
    console.error('Error retrieving order data:', error);
    return NextResponse.json(
      { success: false, error: 'Failed to retrieve order data' },
      { status: 500 }
    );
  }
}

// POST handler - store order data
export async function POST(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    // In NextJS 13+, params needs to be awaited
    const { id } = await Promise.resolve(params);
    
    // Make sure ID is valid to prevent security issues
    if (!id || id.includes('/') || id.includes('..')) {
      return NextResponse.json(
        { success: false, error: 'Invalid order ID' },
        { status: 400 }
      );
    }
    
    // Get request body
    const orderData = await request.json();
    
    // Add timestamp if not present
    if (!orderData.timestamp) {
      orderData.timestamp = new Date().toISOString();
    }
    
    // Construct blob path
    const blobPath = `orders/${id}.json`;
    
    // Store data in Vercel Blob
    const blobUrl = await storeFileInBlob(JSON.stringify(orderData, null, 2), blobPath);
    
    if (!blobUrl) {
      return NextResponse.json(
        { success: false, error: 'Failed to store order data' },
        { status: 500 }
      );
    }
    
    console.log(`Order data saved to Blob at ${blobUrl}`);
    
    return NextResponse.json({
      success: true,
      message: 'Order data saved successfully'
    });
  } catch (error) {
    console.error('Error storing order data:', error);
    return NextResponse.json(
      { success: false, error: 'Failed to store order data' },
      { status: 500 }
    );
  }
}