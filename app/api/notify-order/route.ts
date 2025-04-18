import { NextRequest, NextResponse } from 'next/server';
import { WebClient } from '@slack/web-api';
import { IncomingWebhook } from '@slack/webhook';
import { OrderNotification } from '@/lib/slack';

// Initialize Slack clients
const slackClient = new WebClient(process.env.SLACK_BOT_TOKEN);
const webhook = new IncomingWebhook(process.env.SLACK_WEBHOOK_URL || '');
const channelId = process.env.SLACK_CHANNEL_ID || '';

export async function POST(req: NextRequest) {
  try {
    // Parse the multipart form data
    const formData = await req.formData();
    
    // Get the order data
    const orderJson = formData.get('order');
    if (!orderJson || typeof orderJson !== 'string') {
      return NextResponse.json(
        { error: 'Order data is required' },
        { status: 400 }
      );
    }
    
    const order: OrderNotification = JSON.parse(orderJson);
    
    // Format the message for Slack
    const message = formatOrderMessage(order);
    
    // Send the message to Slack
    await webhook.send({
      text: `New Order: ${order.orderId}`,
      blocks: message,
    });
    
    // Upload files if provided
    const filePromises = [];
    for (let i = 0; formData.has(`file${i}`); i++) {
      const file = formData.get(`file${i}`) as File;
      if (file) {
        const buffer = Buffer.from(await file.arrayBuffer());
        
        filePromises.push(
          slackClient.files.upload({
            channels: channelId,
            filename: file.name,
            file: buffer,
            initial_comment: `File for Order ${order.orderId}: ${file.name}`,
          })
        );
      }
    }
    
    // Wait for all file uploads to complete
    if (filePromises.length > 0) {
      await Promise.all(filePromises);
    }
    
    return NextResponse.json({
      success: true,
      message: 'Order notification sent to Slack',
    });
  } catch (error) {
    console.error('Error sending order notification to Slack:', error);
    
    return NextResponse.json(
      { 
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error occurred' 
      },
      { status: 500 }
    );
  }
}

/**
 * Format the order message for Slack
 * 
 * @param order Order notification data
 * @returns Slack message blocks
 */
function formatOrderMessage(order: OrderNotification) {
  // Format the items
  const itemsText = order.items.map(item => {
    return `• ${item.quantity}x ${item.fileName} (${item.process}, ${item.material}, ${item.finish}) - $${item.price.toFixed(2)}`;
  }).join('\n');
  
  // Format the shipping address
  const addressText = [
    order.shippingAddress.line1,
    order.shippingAddress.line2,
    `${order.shippingAddress.city}, ${order.shippingAddress.state} ${order.shippingAddress.postal_code}`,
    order.shippingAddress.country,
  ].filter(Boolean).join('\n');
  
  // Create the message blocks
  return [
    {
      type: 'header',
      text: {
        type: 'plain_text',
        text: `🛒 New Order: ${order.orderId}`,
        emoji: true,
      },
    },
    {
      type: 'section',
      fields: [
        {
          type: 'mrkdwn',
          text: `*Customer:*\n${order.customerName}`,
        },
        {
          type: 'mrkdwn',
          text: `*Email:*\n${order.customerEmail}`,
        },
      ],
    },
    {
      type: 'section',
      text: {
        type: 'mrkdwn',
        text: `*Items:*\n${itemsText}`,
      },
    },
    {
      type: 'section',
      fields: [
        {
          type: 'mrkdwn',
          text: `*Total:*\n$${order.totalPrice.toFixed(2)} ${order.currency.toUpperCase()}`,
        },
        {
          type: 'mrkdwn',
          text: `*Shipping Address:*\n${addressText}`,
        },
      ],
    },
    ...(order.specialInstructions ? [
      {
        type: 'section',
        text: {
          type: 'mrkdwn',
          text: `*Special Instructions:*\n${order.specialInstructions}`,
        },
      },
    ] : []),
    {
      type: 'context',
      elements: [
        {
          type: 'mrkdwn',
          text: `Order received at ${new Date().toLocaleString()}`,
        },
      ],
    },
  ];
}
