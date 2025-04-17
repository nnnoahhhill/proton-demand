/**
 * Slack notification service
 */

/**
 * Interface for contact form submission
 */
export interface ContactSubmission {
  name: string;
  email: string;
  subject: string;
  message: string;
  files?: File[];
}

/**
 * Interface for order notification
 */
export interface OrderNotification {
  orderId: string;
  customerName: string;
  customerEmail: string;
  items: Array<{
    id: string;
    fileName: string;
    process: string;
    material: string;
    finish: string;
    quantity: number;
    price: number;
  }>;
  totalPrice: number;
  currency: string;
  specialInstructions?: string;
  shippingAddress: {
    line1: string;
    line2?: string;
    city: string;
    state: string;
    postal_code: string;
    country: string;
  };
  files?: File[];
  modelFiles?: File[]; // 3D model files to attach to Slack message
  orderDate?: Date; // Date the order was placed
}

/**
 * Send a contact form submission to Slack
 * 
 * @param contact Contact form data
 * @returns Promise resolving to success status
 */
export async function sendContactNotification(contact: ContactSubmission): Promise<{ success: boolean; message?: string }> {
  try {
    // Create a FormData object to send files
    const formData = new FormData();
    
    // Add contact data as JSON
    formData.append('contact', JSON.stringify(contact));
    
    // Add files if provided
    if (contact.files && contact.files.length > 0) {
      contact.files.forEach((file, index) => {
        formData.append(`file${index}`, file);
      });
    }
    
    // Get the base URL from environment or use default
    const baseUrl = process.env.NEXT_PUBLIC_BASE_URL || 
                    process.env.VERCEL_URL ? `https://${process.env.VERCEL_URL}` : 
                    'http://localhost:3000';
                    
    // Send the notification to our API endpoint with absolute URL
    const response = await fetch(`${baseUrl}/api/notify-contact`, {
      method: 'POST',
      body: formData,
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || 'Failed to send contact notification');
    }
    
    return await response.json();
  } catch (error) {
    console.error('Error sending contact notification:', error);
    return {
      success: false,
      message: error instanceof Error ? error.message : 'Unknown error occurred',
    };
  }
}

/**
 * Send an order notification to Slack
 * 
 * @param order Order notification data
 * @returns Promise resolving to success status
 */
export async function sendOrderNotification(order: OrderNotification): Promise<{ success: boolean; message?: string }> {
  try {
    // Create a FormData object to send files
    const formData = new FormData();
    
    // Add order data as JSON
    formData.append('order', JSON.stringify(order));
    
    // Add files if provided
    if (order.files && order.files.length > 0) {
      order.files.forEach((file, index) => {
        formData.append(`file${index}`, file);
      });
    }
    
    // Add 3D model files if provided
    if (order.modelFiles && order.modelFiles.length > 0) {
      order.modelFiles.forEach((file, index) => {
        formData.append(`modelFile${index}`, file);
      });
    }
    
    // Add order date if available
    if (order.orderDate) {
      formData.append('orderDate', order.orderDate.toISOString());
    } else {
      formData.append('orderDate', new Date().toISOString());
    }
    
    // Send the notification to our API endpoint
    const response = await fetch('/api/notify-order', {
      method: 'POST',
      body: formData,
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || 'Failed to send notification');
    }
    
    return await response.json();
  } catch (error) {
    console.error('Error sending order notification:', error);
    return {
      success: false,
      message: error instanceof Error ? error.message : 'Unknown error occurred',
    };
  }
}
