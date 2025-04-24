import { NextRequest, NextResponse } from 'next/server';
import { WebClient } from '@slack/web-api';
import { IncomingWebhook } from '@slack/webhook';
import { OrderNotification } from '@/lib/slack';
import path from 'path';
import fs from 'fs';

// Initialize Slack clients
const slackClient = new WebClient(process.env.SLACK_BOT_TOKEN || '');
const webhook = new IncomingWebhook(process.env.SLACK_WEBHOOK_URL || '');
const channelId = process.env.SLACK_CHANNEL_ID || '';

// Check if Slack configuration is available
if (!process.env.SLACK_BOT_TOKEN || !process.env.SLACK_WEBHOOK_URL || !process.env.SLACK_CHANNEL_ID) {
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
    
    // Import the storage module dynamically (since it's a server component)
    const { 
      saveModelFileToFilesystem, 
      initStorage, 
      getModelFileFromFilesystem, 
      getBaseQuoteId,
      findOrderFolder,
      getAllOrderModels
    } = await import('@/lib/storage');
    const fs = await import('fs');
    const { promises: fsPromises } = fs;
    const path = await import('path');
    
    // Make sure storage is initialized before processing files
    await initStorage();
    console.log(`DEBUG: Storage initialized for file processing`);
    
    // Extract the base quote ID for consistency
    const quoteId = order.quoteId || order.items?.[0]?.id || 'NoQuoteID';
    const baseQuoteId = getBaseQuoteId(quoteId);
    console.log(`DEBUG: Using base quote ID: ${baseQuoteId} (from original quote ID: ${quoteId})`);
    
    // Get the payment intent ID / order ID
    const paymentIntentId = order.orderId;
    console.log(`DEBUG: Using payment intent ID: ${paymentIntentId}`);
    
    // Create timestamp in PST for folder naming (if we need to create a new folder)
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
    
    // Find or create the order-specific folder - use payment intent ID as primary identifier
    const orderFolderPath = await findOrderFolder(baseQuoteId, paymentIntentId);
    console.log(`DEBUG: Order folder path: ${orderFolderPath}`);
    
    // Store order data in a JSON file for the success page
    try {
      const ordersDataDir = path.join(process.cwd(), 'storage', 'orders');
      
      // Create the orders directory if it doesn't exist
      try {
        await fsPromises.access(ordersDataDir, fs.constants.F_OK);
        console.log(`DEBUG: Orders data directory exists: ${ordersDataDir}`);
      } catch (e) {
        console.log(`DEBUG: Creating orders data directory: ${ordersDataDir}`);
        await fsPromises.mkdir(ordersDataDir, { recursive: true });
      }
      
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
      
      // Store the data in the orders directory
      const orderDataPath = path.join(ordersDataDir, `${order.orderId}.json`);
      await fsPromises.writeFile(orderDataPath, JSON.stringify(orderData, null, 2));
      console.log(`DEBUG: Stored order data at ${orderDataPath}`);
    } catch (storeError) {
      console.error(`DEBUG: Error storing order data for success page:`, storeError);
    }
    
    // Format the message for Slack
    const message = formatOrderMessage(order, formData, pstTimestamp);
    
    // Send the message to Slack
    await webhook.send({
      text: `New Order: ${order.orderId}`,
      blocks: message,
    });
    console.log(`DEBUG: Using order folder path: ${orderFolderPath}`);
    
    // Get all model files that might be related to this order via quote IDs
    const modelFiles = await getAllOrderModels(baseQuoteId);
    console.log(`DEBUG: Found ${modelFiles.length} model files for order with base quote ID: ${baseQuoteId}`);
    
    // DIRECT FILE SEARCH: Find all STL files in the storage directory
    // This is a critical failsafe to ensure we find and attach all relevant files
    console.log(`DEBUG: Performing direct file search for STL files in storage directory`);
    const modelsDir = path.join(process.cwd(), 'storage', 'models');
    let allStlFiles: {path: string; name: string; metadata?: any}[] = [];
    
    try {
      // Read all files in the models directory
      const allFiles = await fsPromises.readdir(modelsDir);
      
      // Find all STL files
      for (const file of allFiles) {
        if (file.toLowerCase().endsWith('.stl')) {
          const filePath = path.join(modelsDir, file);
          console.log(`DEBUG: Found STL file: ${file}`);
          
          // Check for quote IDs in the file name that match our items
          const matchesOrder = order.items.some(item => {
            return file.includes(item.id) || 
                  (item.baseQuoteId && file.includes(item.baseQuoteId));
          });
          
          // We're no longer using time-based matching, only check quote ID match
          const isRecent = false; // Don't include files based on time
          
          // Check if metadata exists for this file
          const metadataPath = `${filePath}.metadata.json`;
          let metadata = null;
          try {
            const metadataExists = await fsPromises.access(metadataPath)
              .then(() => true)
              .catch(() => false);
            
            if (metadataExists) {
              const metadataContent = await fsPromises.readFile(metadataPath, 'utf8');
              metadata = JSON.parse(metadataContent);
              console.log(`DEBUG: Found metadata for file ${file}`);
            }
          } catch (metaErr) {
            console.log(`DEBUG: Error reading metadata for ${file}: ${metaErr}`);
          }
          
          // Add this file if it matches our order or is recent
          if (matchesOrder || isRecent) {
            console.log(`DEBUG: Adding file ${file} to attachment list`);
            allStlFiles.push({
              path: filePath,
              name: file,
              metadata
            });
          }
        }
      }
      
      console.log(`DEBUG: Found ${allStlFiles.length} STL files that might be related to this order`);
    } catch (scanErr) {
      console.error(`DEBUG: Error scanning directory for STL files: ${scanErr}`);
    }
    
    // Upload files if provided
    const filePromises = [];
    const processedModelFiles = [];
    
    // Regular files (non-models)
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
          
          let actualBuffer: Buffer = buffer;
          let actualFilePath = '';
          let sourceFilePath = '';
          
          if (isPlaceholder) {
            console.log(`DEBUG: Detected placeholder file, will retrieve from server storage`);
            
            // Extract the quote ID from the placeholder content if possible
            const placeholderContent = buffer.toString();
            // Handle both the new extended format and the old simple format
            const newPlaceholderMatch = placeholderContent.match(/SERVER_STORED_FILE:(Q-\d+[-A-Z]?):BASE:(Q-\d+):SUFFIX:([A-Z]?)/);
            const oldPlaceholderMatch = placeholderContent.match(/SERVER_STORED_FILE:(Q-\d+[-A-Z]?)/);
            
            let fileQuoteId, fileBaseQuoteId, fileSuffix;
            
            if (newPlaceholderMatch) {
              // New extended format with baseQuoteId and suffix
              fileQuoteId = newPlaceholderMatch[1];
              fileBaseQuoteId = newPlaceholderMatch[2];
              fileSuffix = newPlaceholderMatch[3];
              console.log(`DEBUG: Extracted extended info from placeholder - quoteId: ${fileQuoteId}, baseQuoteId: ${fileBaseQuoteId}, suffix: ${fileSuffix}`);
            } else if (oldPlaceholderMatch) {
              // Old simple format with just quoteId
              fileQuoteId = oldPlaceholderMatch[1];
              fileBaseQuoteId = baseQuoteId;
              fileSuffix = '';
              console.log(`DEBUG: Extracted simple quoteId from placeholder: ${fileQuoteId}`);
            } else {
              // Fallback to baseQuoteId if no match
              fileQuoteId = baseQuoteId;
              fileBaseQuoteId = baseQuoteId;
              fileSuffix = '';
              console.log(`DEBUG: No quoteId found in placeholder, using baseQuoteId: ${baseQuoteId}`);
            }
            
            // Try to find the actual file on the server
            try {
              const foundFilePath = await getModelFileFromFilesystem(fileQuoteId, modelFile.name);
              if (foundFilePath) {
                sourceFilePath = foundFilePath;
                console.log(`DEBUG: Found previously stored file at ${sourceFilePath}`);
                // We'll use the existing file instead of creating a new one
                actualFilePath = sourceFilePath;
                
                // Read the file into a buffer
                actualBuffer = await fsPromises.readFile(sourceFilePath);
                console.log(`DEBUG: Read existing file into buffer: ${actualBuffer.length} bytes`);
                
                // Copy this file to the order-specific folder if it exists
                if (orderFolderPath) {
                  try {
                    const fileName = path.basename(sourceFilePath);
                    const targetPath = path.join(orderFolderPath, fileName);
                    
                    // Check if we need to copy the file (don't do it if it's already there)
                    if (sourceFilePath !== targetPath) {
                      console.log(`DEBUG: Copying model file from ${sourceFilePath} to ${targetPath}`);
                      await fsPromises.copyFile(sourceFilePath, targetPath);
                      
                      // Copy metadata file if it exists
                      const metadataPath = `${sourceFilePath}.metadata.json`;
                      try {
                        // Check if metadata file exists
                        try {
                          await fsPromises.access(metadataPath, fs.constants.F_OK);
                          await fsPromises.copyFile(metadataPath, `${targetPath}.metadata.json`);
                          console.log(`DEBUG: Copied metadata file to ${targetPath}.metadata.json`);
                        } catch (accessErr) {
                          console.log(`DEBUG: No metadata file found at ${metadataPath}`);
                        }
                      } catch (metaErr) {
                        console.log(`DEBUG: No metadata file found at ${metadataPath}`);
                      }
                    } else {
                      console.log(`DEBUG: File is already in the order folder, skipping copy`);
                    }
                  } catch (copyError) {
                    console.error(`DEBUG: Error copying file to order folder:`, copyError);
                  }
                }
              } else {
                console.log(`DEBUG: No previously stored file found for quote ${fileQuoteId}`);
                // Continue with the placeholder buffer, which will create a minimal file
              }
            } catch (findError) {
              console.error(`DEBUG: Error finding previously stored file:`, findError);
            }
          } else {
            console.log(`DEBUG: Using uploaded file buffer: ${buffer.length} bytes`);
            actualBuffer = buffer;
          }
          
          // Add to processedModelFiles
          processedModelFiles.push({
            name: modelFile.name,
            buffer: actualBuffer,
            filePath: actualFilePath,
            sourceFilePath: sourceFilePath
          });
        } catch (fileError) {
          console.error(`DEBUG: Error processing model file:`, fileError);
        }
      }
    }
    
    // If we have models from the database, add them to the processedModelFiles list
    // and copy them to the order folder
    for (const modelFile of modelFiles) {
      // Skip if we already have this file processed
      const isDuplicate = processedModelFiles.some(
        pf => pf.name === modelFile.fileName || pf.filePath === modelFile.filePath
      );
      
      if (isDuplicate) {
        console.log(`DEBUG: Skipping duplicate model file: ${modelFile.fileName}`);
        continue;
      }
      
      try {
        console.log(`DEBUG: Adding model file from database: ${modelFile.fileName} at ${modelFile.filePath}`);
        
        if (modelFile.filePath) {
          // Read the file into a buffer for Slack upload
          const fileBuffer = await fsPromises.readFile(modelFile.filePath);
          
          // Add to processed files list for Slack upload
          processedModelFiles.push({
            name: modelFile.fileName,
            buffer: fileBuffer,
            filePath: modelFile.filePath,
            sourceFilePath: modelFile.filePath
          });
          
          // Also copy this file to the order-specific folder if needed
          if (orderFolderPath) {
            try {
              const targetPath = path.join(orderFolderPath, modelFile.fileName);
              
              // Check if we need to copy the file (don't do it if it's already there)
              if (modelFile.filePath !== targetPath) {
                console.log(`DEBUG: Copying model file from ${modelFile.filePath} to ${targetPath}`);
                await fsPromises.copyFile(modelFile.filePath, targetPath);
                
                // Copy metadata file if it exists
                const metadataPath = `${modelFile.filePath}.metadata.json`;
                try {
                  // Check if metadata file exists
                  try {
                    await fsPromises.access(metadataPath, fs.constants.F_OK);
                    await fsPromises.copyFile(metadataPath, `${targetPath}.metadata.json`);
                    console.log(`DEBUG: Copied metadata file to ${targetPath}.metadata.json`);
                  } catch (accessErr) {
                    console.log(`DEBUG: No metadata file found at ${metadataPath}`);
                  }
                } catch (metaErr) {
                  console.log(`DEBUG: No metadata file found at ${metadataPath}`);
                }
              } else {
                console.log(`DEBUG: File is already in the order folder, skipping copy`);
              }
            } catch (copyError) {
              console.error(`DEBUG: Error copying file to order folder:`, copyError);
            }
          }
        }
      } catch (readError) {
        console.error(`DEBUG: Error reading model file from database:`, readError);
      }
    }
    
    // Directly upload STL files found in the storage directory
    console.log(`DEBUG: Uploading ${allStlFiles.length} STL files directly from storage`);
    for (const stlFile of allStlFiles) {
      try {
        // Read the file content
        const fileBuffer = await fsPromises.readFile(stlFile.path);
        
        // Get metadata information if available
        let metadataInfo = '';
        if (stlFile.metadata) {
          const meta = stlFile.metadata;
          const tech = meta.technology || 'Unknown';
          const techLabel = ['SLA', 'SLS', 'FDM'].includes(tech) ? `${tech} 3D Printing` : tech;
          const materialDisplayName = getMaterialDisplayName(meta.material || 'Unknown');
          metadataInfo = `\nFile: ${stlFile.name}\nTechnology: ${techLabel}\nMaterial: ${materialDisplayName}\nQuantity: ${meta.quantity || '1'}`;
        }
        
        // Queue up slack file upload
        filePromises.push(
          slackClient.files.upload({
            channels: channelId,
            filename: stlFile.name,
            file: fileBuffer,
            filetype: 'binary', // STL files are binary
            initial_comment: `${metadataInfo}`,
          }).then(result => {
            console.log(`DEBUG: Successfully uploaded STL file to Slack: ${result.file?.id}`);
            return result;
          }).catch(error => {
            console.error(`DEBUG: Error uploading STL file to Slack:`, error);
            return error;
          })
        );
      } catch (fileError) {
        console.error(`DEBUG: Error reading STL file ${stlFile.path}:`, fileError);
      }
    }
    
    // Upload all processed model files to Slack
    console.log(`DEBUG: Uploading ${processedModelFiles.length} model files from placeholders to Slack`);
    for (const modelFile of processedModelFiles) {
      try {
        filePromises.push(
          slackClient.files.upload({
            channels: channelId,
            filename: modelFile.name,
            file: modelFile.buffer,
            filetype: getFileType(modelFile.name.split('.').pop() || ''),
            initial_comment: `File: ${modelFile.name}\nTechnology: ${getFormattedTechnology(modelFile.metadata?.technology || 'Unknown')}\nMaterial: ${getMaterialDisplayName(modelFile.metadata?.material || 'Unknown')}\nQuantity: ${modelFile.metadata?.quantity || '1'}`,
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

