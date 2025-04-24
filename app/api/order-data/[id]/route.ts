/**
 * API route for storing and retrieving order data
 * Used by the checkout form to store order details after payment
 * Used by the order success page to display order details
 */
import { NextRequest, NextResponse } from 'next/server';
import { writeFile, readFile, mkdir } from 'fs/promises';
import { existsSync } from 'fs';
import path from 'path';
import { constants } from 'fs';
import { access } from 'fs/promises';

// Base storage directory for order data
const projectRoot = process.cwd();
const ORDERS_DATA_DIR = path.join(projectRoot, 'storage', 'orders');

// Initialize the orders directory if it doesn't exist
async function initOrdersDirectory() {
  try {
    try {
      await access(ORDERS_DATA_DIR, constants.F_OK);
      console.log(`Orders directory exists: ${ORDERS_DATA_DIR}`);
    } catch (e) {
      console.log(`Creating orders directory: ${ORDERS_DATA_DIR}`);
      await mkdir(ORDERS_DATA_DIR, { recursive: true });
    }
    return true;
  } catch (error) {
    console.error('Error initializing orders directory:', error);
    return false;
  }
}

// GET handler - retrieve order data
export async function GET(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    // In NextJS 13+, params needs to be awaited
    const { id } = await Promise.resolve(params);
    
    // Make sure ID is valid to prevent directory traversal
    if (!id || id.includes('/') || id.includes('..')) {
      return NextResponse.json(
        { success: false, error: 'Invalid order ID' },
        { status: 400 }
      );
    }
    
    // Initialize directory
    await initOrdersDirectory();
    
    // Construct file path
    const filePath = path.join(ORDERS_DATA_DIR, `${id}.json`);
    
    // Check if file exists
    if (!existsSync(filePath)) {
      return NextResponse.json(
        { success: false, error: 'Order data not found' },
        { status: 404 }
      );
    }
    
    // Read file
    const data = await readFile(filePath, 'utf8');
    const orderData = JSON.parse(data);
    
    return NextResponse.json({
      success: true,
      order: orderData
    });
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
    
    // Make sure ID is valid to prevent directory traversal
    if (!id || id.includes('/') || id.includes('..')) {
      return NextResponse.json(
        { success: false, error: 'Invalid order ID' },
        { status: 400 }
      );
    }
    
    // Get request body
    const orderData = await request.json();
    
    // Initialize directory
    await initOrdersDirectory();
    
    // Construct file path
    const filePath = path.join(ORDERS_DATA_DIR, `${id}.json`);
    
    // Add timestamp if not present
    if (!orderData.timestamp) {
      orderData.timestamp = new Date().toISOString();
    }
    
    // Write data to file
    await writeFile(filePath, JSON.stringify(orderData, null, 2));
    
    console.log(`Order data saved to ${filePath}`);
    
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