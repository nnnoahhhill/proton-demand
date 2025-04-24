import { NextRequest, NextResponse } from 'next/server';
import { WebClient } from '@slack/web-api';
import { IncomingWebhook } from '@slack/webhook';
import { OrderNotification } from '@/lib/slack';
import { storeFileInBlob, getFileFromBlob, listFilesInBlob } from '@/lib/blob';
import path from 'path';

// Set longer timeout and config for large file uploads
export const maxDuration = 60;
export const config = {
  runtime: 'nodejs',
};

// Initialize Slack clients
const slackClient = new WebClient(process.env.SLACK_BOT_TOKEN || '');
const webhook = new IncomingWebhook(process.env.SLACK_WEBHOOK_URL || '');
// Use the correct channel ID from env vars (SLACK_UPLOAD_CHANNEL_ID instead of SLACK_CHANNEL_ID)
const channelId = process.env.SLACK_UPLOAD_CHANNEL_ID || '';

// Check if Slack configuration is available
if (!process.env.SLACK_BOT_TOKEN || !process.env.SLACK_WEBHOOK_URL || !process.env.SLACK_UPLOAD_CHANNEL_ID) {
  console.warn('WARNING: Slack configuration is incomplete. Notifications may not work correctly.');
}

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
    console.log(`DEBUG: Processing order notification:`, JSON.stringify(order, null, 2));
    
    // Import the getBaseQuoteId function dynamically (since it's a server component)
    const { getBaseQuoteId } = await import('@/lib/storage');
    
    // Extract the base quote ID for consistency
    const quoteId = order.quoteId || order.items?.[0]?.id || 'NoQuoteID';
    const baseQuoteId = getBaseQuoteId(quoteId);
    console.log(`DEBUG: Using base quote ID: ${baseQuoteId} (from original quote ID: ${quoteId})`);
    
    // Get the payment intent ID / order ID
    const paymentIntentId = order.orderId;
    console.log(`DEBUG: Using payment intent ID: ${paymentIntentId}`);
    
    // Create timestamp in PST for naming
    const now = new Date();
    const pstOptions = { 
      timeZone: 'America/Los_Angeles',
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false
    };
    const pstTimestamp = now.toLocaleString('en-US', pstOptions as any)
      .replace(/[\/,:\s]/g, '-');
    
    // Store order data in Vercel Blob for the success page
    try {
      // Calculate total
      const totalAmount = order.items.reduce((sum, item) => {
        const price = typeof item.price === 'number' ? item.price : 0;
        const quantity = item.quantity || 1;
        return sum + (price * quantity);
      }, 0);
      
      // Create a well-formatted order data JSON
      const orderData = {
        paymentIntentId: order.orderId,
        customerName: order.customerName,
        customerEmail: order.customerEmail,
        totalAmount: order.totalPrice || totalAmount,
        items: order.items.map(item => ({
          id: item.id,
          name: item.fileName,
          price: item.price,
          quantity: item.quantity || 1,
          material: item.material || 'Default',
          process: item.process || 'Standard',
          technology: item.technology || item.process || 'Standard',
        })),
        timestamp: new Date().toISOString(),
        shippingAddress: order.shippingAddress
      };
      
      // Store the data in Vercel Blob
      const blobPath = `orders/${order.orderId}.json`;
      await storeFileInBlob(JSON.stringify(orderData, null, 2), blobPath);
      console.log(`DEBUG: Stored order data in Blob at ${blobPath}`);
    } catch (storeError) {
      console.error(`DEBUG: Error storing order data for success page:`, storeError);
    }
    
    // Format the message for Slack
    const message = formatOrderMessage(order, formData, pstTimestamp);
    
    // Send the message to Slack using the Webhook
    try {
      console.log(`DEBUG: Sending notification to Slack webhook`);
      await webhook.send({
        text: `New Order: ${order.orderId}`,
        blocks: message,
      });
      console.log(`DEBUG: Successfully sent notification to Slack webhook`);
    } catch (webhookError) {
      console.error(`DEBUG: Error sending to Slack webhook:`, webhookError);
      
      // Fallback: Try using the Slack client instead
      try {
        console.log(`DEBUG: Attempting fallback with slack client`);
        await slackClient.chat.postMessage({
          channel: channelId,
          text: `New Order: ${order.orderId}`,
          blocks: message,
        });
        console.log(`DEBUG: Successfully sent fallback notification via slack client`);
      } catch (clientError) {
        console.error(`DEBUG: Error sending fallback via slack client:`, clientError);
      }
    }
    
    // Using any[] type because Slack's SDK response types are complex
    const filePromises: any[] = [];
    
    // Regular files (non-models)
    for (let i = 0; formData.has(`file${i}`); i++) {
      const file = formData.get(`file${i}`) as File;
      if (file) {
        // First upload to Blob storage
        const blobPath = `orders/${order.orderId}/files/${file.name}`;
        const blobUrl = await storeFileInBlob(file, blobPath);
        
        // Then upload to Slack
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
    
    // Process explicitly uploaded model files
    for (let i = 0; formData.has(`modelFile${i}`); i++) {
      const modelFile = formData.get(`modelFile${i}`) as File;
      console.log(`DEBUG: Processing modelFile${i}:`, modelFile?.name, modelFile?.size, modelFile?.type);
      
      if (modelFile) {
        try {
          // Check if this is a placeholder that indicates a server-stored file
          const buffer = Buffer.from(await modelFile.arrayBuffer());
          const isPlaceholder = buffer.length < 1024 && 
                              buffer.toString().includes('SERVER_STORED_FILE:');
          
          let blobUrl = '';
          let actualBuffer = buffer;
          
          if (isPlaceholder) {
            console.log(`DEBUG: Detected placeholder file, will check Blob storage`);
            
            // Extract the quote ID from the placeholder content if possible
            const placeholderContent = buffer.toString();
            // Handle both the new extended format and the old simple format
            const newPlaceholderMatch = placeholderContent.match(/SERVER_STORED_FILE:(Q-\d+[-A-Z]?):BASE:(Q-\d+):SUFFIX:([A-Z]?)/);
            const oldPlaceholderMatch = placeholderContent.match(/SERVER_STORED_FILE:(Q-\d+[-A-Z]?)/);
            
            let fileQuoteId;
            
            if (newPlaceholderMatch) {
              fileQuoteId = newPlaceholderMatch[1];
              console.log(`DEBUG: Extracted extended info from placeholder - quoteId: ${fileQuoteId}`);
            } else if (oldPlaceholderMatch) {
              fileQuoteId = oldPlaceholderMatch[1];
              console.log(`DEBUG: Extracted simple quoteId from placeholder: ${fileQuoteId}`);
            } else {
              fileQuoteId = baseQuoteId;
              console.log(`DEBUG: No quoteId found in placeholder, using baseQuoteId: ${baseQuoteId}`);
            }
            
            // Try to find the file in Blob storage
            try {
              // List files with this quoteId and filename
              const matchingBlobs = await listFilesInBlob(`models/${fileQuoteId}/`);
              const modelFileBlobs = matchingBlobs.filter(b => 
                path.basename(b.pathname) === modelFile.name || 
                b.pathname.includes(modelFile.name)
              );
              
              if (modelFileBlobs.length > 0) {
                // Use the first matching blob
                blobUrl = modelFileBlobs[0].url;
                console.log(`DEBUG: Found previously stored file in Blob: ${blobUrl}`);
                
                // Get the file buffer
                const fileBuffer = await getFileFromBlob(blobUrl);
                if (fileBuffer) {
                  actualBuffer = Buffer.from(fileBuffer);
                  console.log(`DEBUG: Got existing file from Blob: ${actualBuffer.length} bytes`);
                }
                
                // Also copy this file to the order's folder in Blob
                const orderBlobPath = `orders/${order.orderId}/models/${modelFile.name}`;
                await storeFileInBlob(actualBuffer, orderBlobPath);
                console.log(`DEBUG: Copied file to order Blob folder: ${orderBlobPath}`);
              } else {
                console.log(`DEBUG: No previously stored file found in Blob for quote ${fileQuoteId}`);
                // Continue with the placeholder buffer
                
                // Store the placeholder in Blob storage
                const placeholderPath = `orders/${order.orderId}/models/${fileQuoteId}/${modelFile.name}`;
                const result = await storeFileInBlob(buffer, placeholderPath);
                blobUrl = result || '';
              }
            } catch (findError) {
              console.error(`DEBUG: Error finding previously stored file in Blob:`, findError);
            }
          } else {
            console.log(`DEBUG: Using uploaded file buffer: ${buffer.length} bytes`);
            // Store the file in Blob storage
            const filePath = `models/${baseQuoteId}/${modelFile.name}`;
            const result = await storeFileInBlob(buffer, filePath);
            blobUrl = result || '';
            
            // Also store in order folder
            const orderFilePath = `orders/${order.orderId}/models/${modelFile.name}`;
            await storeFileInBlob(buffer, orderFilePath);
          }
          
          // Upload to Slack
          filePromises.push(
            slackClient.files.upload({
              channels: channelId,
              filename: modelFile.name,
              file: actualBuffer,
              filetype: getFileType(modelFile.name.split('.').pop() || ''),
              initial_comment: `File: ${modelFile.name} for Order: ${order.orderId}\nQuote ID: ${baseQuoteId}`,
            }).then(result => {
              console.log(`DEBUG: Successfully uploaded model file to Slack: ${result.file?.id}`);
              return result;
            }).catch(error => {
              console.error(`DEBUG: Error uploading model file to Slack:`, error);
              return error;
            })
          );
        } catch (fileError) {
          console.error(`DEBUG: Error processing model file:`, fileError);
        }
      }
    }
    
    // Look for any STL files in Blob storage that might be related to this order
    console.log(`DEBUG: Checking Blob storage for STL files related to this order`);
    try {
      // Try to list files for this quote ID
      const stlFiles = (await listFilesInBlob(`models/${baseQuoteId}/`))
        .filter(b => b.pathname.toLowerCase().endsWith('.stl'));
      
      console.log(`DEBUG: Found ${stlFiles.length} STL files in Blob related to quote ID: ${baseQuoteId}`);
      
      // Upload each STL file to Slack
      for (const stlFile of stlFiles) {
        try {
          // Get the file content
          const fileBuffer = await getFileFromBlob(stlFile.url);
          if (!fileBuffer) continue;
          
          const fileName = path.basename(stlFile.pathname);
          
          // Copy to order folder in Blob
          const orderBlobPath = `orders/${order.orderId}/models/${fileName}`;
          await storeFileInBlob(fileBuffer, orderBlobPath);
          console.log(`DEBUG: Copied STL file to order Blob folder: ${orderBlobPath}`);
          
          // Queue up Slack file upload
          filePromises.push(
            slackClient.files.upload({
              channels: channelId,
              filename: fileName,
              file: fileBuffer,
              filetype: 'binary', // STL files are binary
              initial_comment: `STL File: ${fileName} for Order: ${order.orderId}`,
            }).then(result => {
              console.log(`DEBUG: Successfully uploaded STL file to Slack: ${result.file?.id}`);
              return result;
            }).catch(error => {
              console.error(`DEBUG: Error uploading STL file to Slack:`, error);
              return error;
            })
          );
        } catch (fileError) {
          console.error(`DEBUG: Error processing STL file from Blob:`, fileError);
        }
      }
    } catch (listError) {
      console.error(`DEBUG: Error listing STL files in Blob:`, listError);
    }
    
    // Also check for any files already in the order's Blob folder
    // This is important for orders that were previously processed
    try {
      const orderFiles = await listFilesInBlob(`orders/${order.orderId}/`);
      console.log(`DEBUG: Found ${orderFiles.length} files already in order folder in Blob`);
      
      // Upload any files we haven't already processed
      for (const orderFile of orderFiles) {
        // Skip if this file was already processed
        const fileBasename = path.basename(orderFile.pathname);
        if (filePromises.some(p => {
          // Check if this promise is for a file we've already processed
          return p && typeof p === 'object' && 'filename' in p && p.filename === fileBasename;
        })) {
          console.log(`DEBUG: Skipping already processed file: ${orderFile.pathname}`);
          continue;
        }
        
        try {
          const fileBuffer = await getFileFromBlob(orderFile.url);
          if (!fileBuffer) continue;
          
          const fileName = path.basename(orderFile.pathname);
          
          // Upload to Slack
          filePromises.push(
            slackClient.files.upload({
              channels: channelId,
              filename: fileName,
              file: fileBuffer,
              filetype: getFileType(fileName.split('.').pop() || ''),
              initial_comment: `File: ${fileName} for Order: ${order.orderId}`,
            }).then(result => {
              console.log(`DEBUG: Successfully uploaded order file to Slack: ${result.file?.id}`);
              return result;
            }).catch(error => {
              console.error(`DEBUG: Error uploading order file to Slack:`, error);
              return error;
            })
          );
        } catch (fileError) {
          console.error(`DEBUG: Error processing file from order folder in Blob:`, fileError);
        }
      }
    } catch (listError) {
      console.error(`DEBUG: Error listing files in order folder in Blob:`, listError);
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
 * Format technology name for display
 * 
 * @param technology The technology string
 * @returns Formatted technology name
 */
function getFormattedTechnology(technology: string): string {
  // Add "3D Printing" for common 3D printing technologies
  if (['SLA', 'SLS', 'FDM'].includes(technology)) {
    return `${technology} 3D Printing`;
  }
  return technology;
}

/**
 * Get display name for material from its ID
 * 
 * @param materialId The material ID
 * @returns Human-readable material name
 */
function getMaterialDisplayName(materialId: string): string {
  // Material ID to display name mapping based on backend materials.json
  const materialMappings: Record<string, string> = {
    'sla_resin_standard': 'Standard Resin',
    'PLA': 'PLA',
    'ABS': 'ABS',
    'PETG': 'PETG',
    'TPU': 'TPU',
    'NYLON_12': 'Nylon 12',
    'ASA': 'ASA',
    'NYLON_12_WHITE': 'Nylon 12 (White)',
    'NYLON_12_BLACK': 'Nylon 12 (Black)',
    'STANDARD_RESIN': 'Standard Resin',
    'ALUMINUM_6061': 'Aluminum 6061',
    'MILD_STEEL': 'Mild Steel',
    'STAINLESS_STEEL_304': 'Stainless Steel 304',
    'STAINLESS_STEEL_316': 'Stainless Steel 316',
    'TITANIUM': 'Titanium',
    'COPPER': 'Copper',
    'BRASS': 'Brass'
  };
  
  // Try to find readable name, or use the ID if not found
  return materialMappings[materialId] || materialId;
}

/**
 * Format the order message for Slack
 * 
 * @param order Order notification data
 * @param formData Form data from request
 * @param timestamp Timestamp string in PST
 * @returns Slack message blocks
 */
function formatOrderMessage(order: OrderNotification, formData: FormData, timestamp: string) {
  console.log(`DEBUG: Formatting order message for Slack - Order:`, JSON.stringify(order, null, 2));
  
  // Get the order date and format in PST/PDT timezone
  const orderDateStr = formData.get('orderDate') as string;
  const orderDate = orderDateStr 
    ? new Date(orderDateStr)
    : new Date();
  
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
  
  // Format the shipping address as a single line - country on same line
  const addressComponents = [
    order.shippingAddress.line1,
    order.shippingAddress.line2,
    `${order.shippingAddress.city}, ${order.shippingAddress.state} ${order.shippingAddress.postal_code}`,
    order.shippingAddress.country,
  ].filter(Boolean);
  const addressText = addressComponents.join(', ');
  
  // Calculate total payment amount
  const totalAmount = order.items.reduce((sum, item) => {
    const price = typeof item.price === 'number' ? item.price : 0;
    const quantity = item.quantity || 1;
    return sum + (price * quantity);
  }, 0);
  
  // Use totalPrice from order if available, otherwise use calculated amount
  const totalWithShipping = order.totalPrice || totalAmount;
  
  // Format the items list according to the requested format
  let itemsText = '';
  
  // Check if we have any items in the order
  if (order.items && order.items.length > 0) {
    order.items.forEach((item, index) => {
      const quantity = item.quantity || 1;
      const technology = item.technology || item.process || 'Standard';
      const material = item.material || 'Not specified';
      
      // Make each part very clear with better formatting
      itemsText += `*${index + 1}.* ${item.fileName || 'Unnamed File'}\n`;
      itemsText += `• *QUANTITY:* ${quantity}\n`;
      const techLabel = ['SLA', 'SLS', 'FDM'].includes(technology) ? `${technology} 3D Printing` : technology;
      itemsText += `• *Technology:* ${techLabel}\n`;
      itemsText += `• *Material:* ${getMaterialDisplayName(material)}\n`;
      
      // Add ID information
      if (item.id) {
        itemsText += `• Quote ID: ${item.id}\n`;
      }
      
      // Add any part-specific notes if available (from item.notes or similar)
      if (item.notes) {
        itemsText += `• Notes: ${item.notes}\n`;
      }
      
      // Add a blank line between items except for the last one
      if (index < order.items.length - 1) {
        itemsText += '\n';
      }
    });
  } else {
    // No items found, add a note
    itemsText = "Check the attached files for part information.\n";
  }
  
  // Add general order instructions at the end if provided
  if (order.specialInstructions) {
    itemsText += `\n*GENERAL INSTRUCTIONS:*\n${order.specialInstructions}\n`;
  }
  
  // Create the new message format
  return [
    {
      type: 'section',
      text: {
        type: 'mrkdwn',
        text: `*NEW ORDER: ${order.quoteId || order.orderId}*`
      }
    },
    {
      type: 'section',
      text: {
        type: 'mrkdwn',
        text: `*Date:* ${pacificDate}`
      }
    },
    {
      type: 'section',
      fields: [
        {
          type: 'mrkdwn',
          text: `*Customer:* ${order.customerName}`
        },
        {
          type: 'mrkdwn',
          text: `*Email:* ${order.customerEmail}`
        }
      ]
    },
    {
      type: 'section',
      text: {
        type: 'mrkdwn',
        text: `*PARTS ORDERED:*\n${itemsText}`
      }
    },
    {
      type: 'section',
      text: {
        type: 'mrkdwn',
        text: `*SHIPPING ADDRESS:*\n${addressText}`
      }
    },
    {
      type: 'section',
      text: {
        type: 'mrkdwn',
        text: `*PAYMENT:*\n$${totalWithShipping.toFixed(2)} ${order.currency || 'USD'} (including shipping)`
      }
    },
    {
      type: 'divider'
    },
    {
      type: 'context',
      elements: [
        {
          type: 'mrkdwn',
          text: `ProtonDemand Manufacturing • Order received at ${pacificDate} (PST)`
        }
      ]
    }
  ];
}