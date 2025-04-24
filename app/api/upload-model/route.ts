import { NextRequest, NextResponse } from 'next/server';
import { saveModelFileToFilesystem, initStorage, getBaseQuoteId, findOrderFolder } from '@/lib/storage';
import { join } from 'path';
import { appLogger } from '@/lib/logger';

// Create a logger instance specific to the upload route
const logger = appLogger.child('api:upload-model');

// Set longer timeout for uploads - 60 seconds (Node default is 2 minutes anyway)
export const maxDuration = 60;

/**
 * API endpoint to upload a model file.
 * This is a simpler version of the model file storage
 * that happens during the quote process, but allows us
 * to store the model immediately after quote generation.
 */
export async function POST(req: NextRequest) {
  const logId = `upload-${Date.now()}`;
  logger.info(`POST /api/upload-model called (${logId})`);
  
  try {
    // Initialize storage
    await initStorage();
    
    // Use a timer to track how long the request processing takes
    const startTime = Date.now();
    logger.debug(`Starting upload process (${logId})`);
    
    // Parse the multipart form data
    try {
      // Get the formData with timeout handling
      logger.debug(`Parsing form data (${logId})`);
      const formDataPromise = req.formData();
      const formData = await Promise.race([
        formDataPromise,
        new Promise((_, reject) => 
          setTimeout(() => reject(new Error('Form data parsing timeout')), 30000)
        )
      ]) as FormData;
      
      // Get the model file
      const file = formData.get('file') as File;
      if (!file) {
        logger.error(`No file found in request (${logId})`);
        return NextResponse.json(
          { success: false, error: 'No file found in request' },
          { status: 400 }
        );
      }
      
      // Check file extension
      const fileName = file.name;
      const fileExtension = fileName.split('.').pop()?.toLowerCase() || '';
      logger.info(`Received file: ${fileName}, extension: ${fileExtension}, size: ${(file.size / 1024 / 1024).toFixed(2)}MB (${logId})`);
      
      // Check if it's a supported file type (STL, STEP, STP, OBJ)
      const supportedExtensions = ['stl', 'step', 'stp', 'obj'];
      if (!supportedExtensions.includes(fileExtension)) {
        logger.error(`Unsupported file extension: ${fileExtension} (${logId})`);
        return NextResponse.json(
          { success: false, error: `Unsupported file type: ${fileExtension}. Supported types are: ${supportedExtensions.join(', ')}` },
          { status: 400 }
        );
      }
      
      // Get the quote ID
      const quoteId = formData.get('quoteId') as string;
      if (!quoteId) {
        logger.error(`No quoteId found in request (${logId})`);
        return NextResponse.json(
          { success: false, error: 'Quote ID is required' },
          { status: 400 }
        );
      }
      
      // Extract the base quote ID for consistency
      const baseQuoteId = getBaseQuoteId(quoteId);
      logger.info(`Using base quote ID: ${baseQuoteId} (from original: ${quoteId}) (${logId})`);
      
      // Get or create the order folder
      logger.debug(`Finding/creating order folder for ${baseQuoteId} (${logId})`);
      const orderFolderPath = await findOrderFolder(baseQuoteId);
      if (!orderFolderPath) {
        logger.error(`Failed to find or create order folder (${logId})`);
        return NextResponse.json(
          { success: false, error: 'Failed to create order storage folder' },
          { status: 500 }
        );
      }
      logger.info(`Order folder path: ${orderFolderPath} (${logId})`);
      
      // Get the technology (optional)
      const technology = formData.get('technology') as string;
      
      // Check for FFF/FDM specific configuration
      const isFffConfigured = formData.get('fff_configured') === 'true';
      const material = formData.get('material') as string;
      const weightG = formData.get('weight_g') as string;
      const volumeCm3 = formData.get('volume_cm3') as string;
      
      // Get quantity if available (default to 1 if not provided)
      const quantity = formData.get('quantity') as string || '1';
      
      // Log FFF configuration if available
      if (isFffConfigured) {
        logger.info(`FFF configuration present for ${quoteId} (${logId})`);
        logger.debug(`Material: ${material}, Weight: ${weightG}g, Volume: ${volumeCm3}cm³ (${logId})`);
        
        try {
          // Create or update a configuration file for this model
          // This will be used by the slicing service
          const configData = {
            quoteId,
            baseQuoteId,
            technology: technology || 'FDM',
            material: material || 'PLA',
            quantity: parseInt(quantity) || 1,
            weightG: parseFloat(weightG || '0'),
            volumeCm3: parseFloat(volumeCm3 || '0'),
            configuredAt: new Date().toISOString()
          };
          
          // Path for FFF configuration storage
          const configPath = join(process.cwd(), 'storage', 'fff-configs', `${quoteId}.json`);
          
          // Ensure the directory exists
          const { promises: fs } = require('fs');
          await fs.mkdir(join(process.cwd(), 'storage', 'fff-configs'), { recursive: true });
          
          // Write the configuration file
          await fs.writeFile(configPath, JSON.stringify(configData, null, 2));
          logger.info(`Saved FFF configuration to ${configPath} (${logId})`);
        } catch (configError) {
          logger.error(`Error saving FFF configuration: ${configError} (${logId})`);
          // Continue even if config save fails - we'll still upload the model
        }
      }
      
      logger.info(`Processing upload for file: ${file.name}, quoteId: ${quoteId}, technology: ${technology || 'unknown'} (${logId})`);
      
      try {
        // Convert file to buffer with timeout handling
        logger.debug(`Converting file to buffer (${logId})`);
        const arrayBufferPromise = file.arrayBuffer();
        const arrayBuffer = await Promise.race([
          arrayBufferPromise,
          new Promise((_, reject) => 
            setTimeout(() => reject(new Error('File buffer conversion timeout')), 30000)
          )
        ]) as ArrayBuffer;
        
        const buffer = Buffer.from(arrayBuffer);
        logger.debug(`Converted file to buffer: ${buffer.length} bytes (${logId})`);
        
        // Save the file to the filesystem using our updated storage function
        logger.debug(`Saving file to filesystem (${logId})`);
        const savedFile = await saveModelFileToFilesystem(
          buffer,
          file.name,
          quoteId, // This will handle suffixing internally
          undefined, // No order number yet
          'Uploaded Model', // Generic part name
          { // Add metadata including FFF configuration
            technology,
            isFffConfigured: isFffConfigured ? 'true' : 'false',
            material: material || '',
            quantity: quantity, // Add quantity to metadata
            weightG: weightG || '',
            volumeCm3: volumeCm3 || '',
            baseQuoteId, // Include base quote ID for reference
            uploadId: logId // Add tracking ID for this upload
          }
        );
        
        if (!savedFile) {
          logger.error(`Failed to save model file (${logId})`);
          return NextResponse.json(
            { success: false, error: 'Failed to save model file' },
            { status: 500 }
          );
        }
        
        const elapsedTime = Date.now() - startTime;
        logger.info(`Successfully saved model file: ${savedFile.filePath} in ${elapsedTime}ms (${logId})`);
        
        // Return the file information with more debugging details
        const response = {
          success: true,
          message: 'Model file uploaded successfully',
          fileName: savedFile.fileName,
          filePath: savedFile.filePath,
          fileUrl: savedFile.fileUrl,
          fileSize: savedFile.fileSize,
          fileType: savedFile.fileType,
          quoteId: savedFile.quoteId,
          baseQuoteId: savedFile.metadata?.baseQuoteId || baseQuoteId,
          suffix: savedFile.metadata?.suffix || '',
          orderFolderPath: savedFile.metadata?.orderFolderPath || orderFolderPath,
          storagePath: join(process.cwd(), 'storage', 'models'),
          fffConfigured: isFffConfigured,
          processingTime: elapsedTime
        };
        
        logger.info(`Upload complete, returning success response (${logId})`);
        return NextResponse.json(response);
      } catch (bufferError) {
        logger.error(`Error processing file buffer: ${bufferError} (${logId})`);
        return NextResponse.json(
          { 
            success: false, 
            error: `Error processing file: ${bufferError instanceof Error ? bufferError.message : 'Unknown error'}`,
            errorType: 'BUFFER_ERROR',
            requestId: logId
          },
          { status: 500 }
        );
      }
    } catch (formDataError) {
      logger.error(`Error parsing form data: ${formDataError} (${logId})`);
      return NextResponse.json(
        { 
          success: false, 
          error: `Error parsing form data: ${formDataError instanceof Error ? formDataError.message : 'Unknown error'}`,
          errorType: 'FORM_DATA_ERROR',
          requestId: logId
        },
        { status: 400 }
      );
    }
    
  } catch (error) {
    logger.error(`Unhandled error in upload handler: ${error} (${logId})`);
    
    // Try to determine the error type for better client-side handling
    let errorType = 'UNKNOWN_ERROR';
    if (error instanceof Error) {
      const errorMessage = error.message.toLowerCase();
      if (errorMessage.includes('timeout')) errorType = 'TIMEOUT_ERROR';
      if (errorMessage.includes('reset') || errorMessage.includes('econnreset')) errorType = 'CONNECTION_RESET';
      if (errorMessage.includes('abort')) errorType = 'REQUEST_ABORTED';
    }
    
    return NextResponse.json(
      { 
        success: false, 
        error: error instanceof Error ? error.message : 'Unknown error occurred',
        errorType,
        requestId: logId
      },
      { status: 500 }
    );
  }
}