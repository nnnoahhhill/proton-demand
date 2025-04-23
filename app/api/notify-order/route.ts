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
    const message = formatOrderMessage(order, formData);
    
    // Send the message to Slack
    await webhook.send({
      text: `New Order: ${order.orderId}`,
      blocks: message,
    });
    
    // Upload files if provided
    const filePromises = [];
    
    // Regular files
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
    
    // 3D model files with special handling
    console.log(`DEBUG: Looking for model files in form data, keys: ${Array.from(formData.keys()).join(', ')}`);
    
    // Import the storage module dynamically (since it's a server component)
    const { saveModelFileToFilesystem, initStorage, getModelFileFromFilesystem } = await import('@/lib/storage');
    
    // Make sure storage is initialized before processing files
    await initStorage();
    console.log(`DEBUG: Storage initialized for file processing`);
    
    for (let i = 0; formData.has(`modelFile${i}`); i++) {
      const modelFile = formData.get(`modelFile${i}`) as File;
      console.log(`DEBUG: Processing modelFile${i}:`, modelFile?.name, modelFile?.size, modelFile?.type);
      
      if (modelFile) {
        try {
          // First get the quote ID either from the order or from any special metadata
          const fileQuoteId = order.quoteId || 'NoQuoteID';
          console.log(`DEBUG: Using quote ID: ${fileQuoteId} for file ${modelFile.name}`);
          
          // Check if this is a placeholder that indicates a server-stored file
          const buffer = Buffer.from(await modelFile.arrayBuffer());
          const isPlaceholder = buffer.length < 1024 && 
                               buffer.toString().includes('SERVER_STORED_FILE:');
          
          let actualBuffer = buffer;
          let actualFilePath = '';
          
          if (isPlaceholder) {
            console.log(`DEBUG: Detected placeholder file, will retrieve from server storage`);
            
            // Try to find the actual file on the server
            // First, check if we can find a previously saved file for this quote ID
            try {
              const storedFilePath = await getModelFileFromFilesystem(fileQuoteId, modelFile.name);
              if (storedFilePath) {
                console.log(`DEBUG: Found previously stored file at ${storedFilePath}`);
                // We'll use the existing file instead of creating a new one
                actualFilePath = storedFilePath;
                
                // Import fs modules dynamically
                const fs = await import('fs');
                const { readFile } = fs.promises;
                
                // Read the file into a buffer
                actualBuffer = await readFile(storedFilePath);
                console.log(`DEBUG: Read existing file into buffer: ${actualBuffer.length} bytes`);
              } else {
                console.log(`DEBUG: No previously stored file found for quote ${fileQuoteId}`);
                // Continue with the placeholder buffer, which will create a minimal file
              }
            } catch (findError) {
              console.error(`DEBUG: Error finding previously stored file:`, findError);
            }
          } else {
            console.log(`DEBUG: Using uploaded file buffer: ${buffer.length} bytes`);
          }
          
          // Create a filename with the quote ID
          let customFileName = modelFile.name;
          if (fileQuoteId !== 'NoQuoteID') {
            const fileExtension = modelFile.name.split('.').pop()?.toLowerCase() || '';
            const nameWithoutExtension = modelFile.name.slice(0, -(fileExtension.length + 1));
            customFileName = `${nameWithoutExtension}_QuoteID-${fileQuoteId}.${fileExtension}`;
            console.log(`DEBUG: Created custom filename with QuoteID: ${customFileName}`);
          }
          
          // Determine file type extension for display
          const fileExtension = modelFile.name.split('.').pop()?.toLowerCase() || '';
          const fileType = getFileType(fileExtension);
          console.log(`DEBUG: File type for extension ${fileExtension}: ${fileType}`);
          
          // Always save the file to the server's filesystem first, BEFORE uploading to Slack
          // Skip if we already have the file path from a previous save
          let savedFile = null;
          if (!actualFilePath) {
            try {
              console.log(`DEBUG: Saving file to filesystem: ${customFileName}`);
              
              // Save the file
              savedFile = await saveModelFileToFilesystem(
                actualBuffer,
                customFileName, // Use the quote ID enhanced filename
                fileQuoteId,
                order.orderId
              );
              
              if (savedFile) {
                console.log(`DEBUG: Successfully saved model file to filesystem: ${savedFile.filePath}`);
                console.log(`DEBUG: File details:`, JSON.stringify(savedFile, null, 2));
                actualFilePath = savedFile.filePath;
              } else {
                console.error(`DEBUG: Failed to save file, saveModelFileToFilesystem returned null`);
              }
            } catch (storageError) {
              console.error('DEBUG: Error saving model file to filesystem:', storageError);
              console.error('Stack trace:', storageError instanceof Error ? storageError.stack : 'No stack trace');
              // Continue with Slack upload even if filesystem storage fails
            }
          }
          
          // Upload to Slack with enhanced filename
          console.log(`DEBUG: Uploading file to Slack: ${customFileName}`);
          try {
            // First upload attempt
            filePromises.push(
              slackClient.files.upload({
                channels: channelId,
                filename: customFileName,
                file: actualBuffer,
                filetype: fileType,
                initial_comment: `🧱 3D Model for Order ${order.orderId}${fileQuoteId !== 'NoQuoteID' ? ` (Quote ${fileQuoteId})` : ''}: ${modelFile.name}`,
              }).then(result => {
                console.log(`DEBUG: Successfully uploaded file to Slack: ${result.file?.id}`);
                return result;
              }).catch(error => {
                console.error(`DEBUG: Error uploading file to Slack:`, error);
                return error;
              })
            );
          } catch (slackError) {
            console.error('DEBUG: Error setting up Slack file upload:', slackError);
          }
        } catch (fileError) {
          console.error(`DEBUG: Error processing model file:`, fileError);
        }
      }
    }
    
    // Wait for all file uploads to complete
    if (filePromises.length > 0) {
      console.log(`DEBUG: Waiting for ${filePromises.length} file uploads to complete`);
      try {
        const results = await Promise.all(filePromises);
        console.log(`DEBUG: All file uploads completed:`, 
          results.map(r => r.file ? `Success: ${r.file.id}` : `Failed`).join(', ')
        );
      } catch (promiseError) {
        console.error(`DEBUG: Error in Promise.all for file uploads:`, promiseError);
      }
    } else {
      console.log(`DEBUG: No files to upload`);
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
 * Helper function to determine file type for Slack
 * 
 * @param extension The file extension
 * @returns The Slack file type
 */
function getFileType(extension: string): string {
  // Map common 3D file extensions to Slack file types
  switch (extension) {
    case 'stl':
    case 'obj':
    case 'step':
    case 'stp':
    case 'glb':
    case 'gltf':
      return 'binary'; // Slack doesn't have specific 3D type, use binary
    default:
      return 'auto'; // Let Slack determine
  }
}

/**
 * Format the order message for Slack
 * 
 * @param order Order notification data
 * @param formData Form data from request
 * @returns Slack message blocks
 */
function formatOrderMessage(order: OrderNotification, formData: FormData) {
  console.log(`DEBUG: Formatting order message for Slack - Order:`, JSON.stringify(order, null, 2));
  
  // Format the items - including technology, material, quantity but removing price
  const itemsText = order.items.map(item => {
    // Make sure to include technology if available
    const technology = item.technology ? `${item.technology}` : 'Standard';
    
    // Ensure we include quantity
    const quantity = item.quantity || 1;
    
    // Format with all requested details
    return `• ${quantity}x ${item.fileName}\n   Technology: *${technology}*\n   Material: *${item.material}*\n   Process: *${item.process}*\n   Finish: *${item.finish}*`;
  }).join('\n\n');
  
  // Format the shipping address
  const addressText = [
    order.shippingAddress.line1,
    order.shippingAddress.line2,
    `${order.shippingAddress.city}, ${order.shippingAddress.state} ${order.shippingAddress.postal_code}`,
    order.shippingAddress.country,
  ].filter(Boolean).join('\n');
  
  // Get the order date and format in PST/PDT timezone
  const orderDateStr = formData.get('orderDate') as string;
  let orderDate = orderDateStr 
    ? new Date(orderDateStr)
    : new Date();
  
  console.log(`DEBUG: Original order date:`, orderDate);
    
  // Format date in Pacific time
  const pacificDate = orderDate.toLocaleString('en-US', {
    timeZone: 'America/Los_Angeles',
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hour12: true
  });
  
  console.log(`DEBUG: Formatted Pacific date:`, pacificDate);
  
  // Always include quote ID if available (make it more prominent)
  const quoteInfoSection = order.quoteId ? [
    {
      type: 'section',
      fields: [
        {
          type: 'mrkdwn',
          text: `*Quote ID:*\n${order.quoteId}`,
        },
        {
          type: 'mrkdwn',
          text: `*Order ID:*\n${order.orderId}`,
        },
      ],
    }
  ] : [
    {
      type: 'section',
      fields: [
        {
          type: 'mrkdwn',
          text: `*Order ID:*\n${order.orderId}`,
        },
      ],
    }
  ];
  
  // Create the message blocks
  return [
    {
      type: 'header',
      text: {
        type: 'plain_text',
        text: `🧱 New Manufacturing Order ${order.quoteId ? `(Quote: ${order.quoteId})` : ''}`,
        emoji: true,
      },
    },
    // Customer information
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
    // Order date in PST
    {
      type: 'section',
      fields: [
        {
          type: 'mrkdwn',
          text: `*Order Date (PST):*\n${pacificDate}`,
        },
      ],
    },
    // Quote and Order IDs
    ...quoteInfoSection,
    // Detailed item information
    {
      type: 'section',
      text: {
        type: 'mrkdwn',
        text: `*Ordered Items:*\n${itemsText}`,
      },
    },
    // Shipping address
    {
      type: 'section',
      fields: [
        {
          type: 'mrkdwn',
          text: `*Shipping Address:*\n${addressText}`,
        },
      ],
    },
    // Special instructions if any
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
      type: 'divider'
    },
    // Footer with timestamp
    {
      type: 'context',
      elements: [
        {
          type: 'mrkdwn',
          text: `ProtonDemand Manufacturing • Order received at ${pacificDate} (PST)`,
        },
      ],
    },
  ];
}
