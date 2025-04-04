/**
 * Slack notification service
 */

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
