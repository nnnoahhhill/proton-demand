import { NextRequest, NextResponse } from 'next/server';
import { join } from 'path';
import { writeFile, mkdir, readdir } from 'fs/promises';
import { saveModelFileToFilesystem, initStorage, getModelsByOrderNumber } from '@/lib/storage';

// Use the centralized storage system instead of a separate path
// This ensures consistency with the rest of the application

export async function POST(req: NextRequest) {
  try {
    console.log('DEBUG: POST /api/models called');
    
    // Initialize storage
    await initStorage();
    
    const formData = await req.formData();
    
    const file = formData.get('file') as File;
    const partName = formData.get('partName') as string;
    const orderNumber = formData.get('orderNumber') as string;
    const metadataJson = formData.get('metadata') as string;
    
    if (!file || !partName || !orderNumber) {
      return NextResponse.json(
        { error: 'File, part name, and order number are required' },
        { status: 400 }
      );
    }
    
    // Get quoteId if it exists, otherwise use orderNumber
    const quoteId = formData.get('quoteId') as string || orderNumber;
    
    console.log(`DEBUG: Processing upload for file: ${file.name}, orderNumber: ${orderNumber}, quoteId: ${quoteId}`);
    console.log(`DEBUG: File size: ${file.size} bytes, type: ${file.type}`);
    
    // Convert file to buffer
    const buffer = Buffer.from(await file.arrayBuffer());
    console.log(`DEBUG: Converted file to buffer: ${buffer.length} bytes`);
    
    // Parse metadata
    const metadata = metadataJson ? JSON.parse(metadataJson) : {};
    
    // Use the central storage system
    const savedFile = await saveModelFileToFilesystem(
      buffer,
      file.name,
      quoteId,
      orderNumber,
      partName
    );
    
    if (!savedFile) {
      console.error('DEBUG: Failed to save model file');
      return NextResponse.json(
        { success: false, error: 'Failed to save model file' },
        { status: 500 }
      );
    }
    
    console.log(`DEBUG: Successfully saved model file: ${savedFile.filePath}`);
    
    // Create model data using the saved file info
    const modelData = {
      id: savedFile.id,
      fileName: savedFile.fileName,
      partName: savedFile.partName,
      orderNumber: savedFile.orderNumber,
      quoteId: savedFile.quoteId,
      fileType: savedFile.fileType,
      uploadDate: savedFile.uploadDate,
      fileSize: savedFile.fileSize,
      fileUrl: savedFile.fileUrl,
      filePath: savedFile.filePath,
      metadata: savedFile.metadata || metadata,
    };
    
    return NextResponse.json({
      success: true,
      model: modelData,
    });
  } catch (error) {
    console.error('Error uploading model:', error);
    
    return NextResponse.json(
      { 
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error occurred' 
      },
      { status: 500 }
    );
  }
}

export async function GET(req: NextRequest) {
  try {
    const { searchParams } = new URL(req.url);
    const orderNumber = searchParams.get('orderNumber');
    const quoteId = searchParams.get('quoteId');
    
    console.log(`DEBUG: GET /api/models called with orderNumber: ${orderNumber}, quoteId: ${quoteId}`);
    
    // We need either orderNumber or quoteId
    if (!orderNumber && !quoteId) {
      return NextResponse.json(
        { error: 'Either Order number or Quote ID is required' },
        { status: 400 }
      );
    }
    
    // Initialize storage to ensure directories exist
    await initStorage();
    
    try {
      let models = [];
      
      // If we have an order number, use that to fetch models
      if (orderNumber) {
        console.log(`DEBUG: Fetching models by order number: ${orderNumber}`);
        
        // This will use the central storage system to look for files by order number
        // Read files from the MODELS_DIR defined in storage.ts
        const files = await readdir(join(process.cwd(), 'storage', 'models'));
        console.log(`DEBUG: Found ${files.length} files in storage/models directory`);
        
        // Filter files that contain the order number - we need a better way to associate files with orders
        // For now, we'll rely on the stored file metadata
        const matchingFiles = files
          .filter(file => !file.endsWith('.meta.json'));
          
        console.log(`DEBUG: Found ${matchingFiles.length} model files (non-metadata)`);
        
        models = matchingFiles.map(file => {
          const fileExtension = file.split('.').pop() || '';
          const filePath = join(process.cwd(), 'storage', 'models', file);
          
          // Extract quoteId from filename if possible (format is quoteId_filename)
          const fileQuoteId = file.split('_')[0];
          const originalFileName = file.split('_').slice(1).join('_');
          
          console.log(`DEBUG: Processing file: ${file}, quoteId: ${fileQuoteId}, fileName: ${originalFileName}`);
          
          // Create a file URL that will work with our API route
          // The format needs to be consistent with how we look up files
          const encodedFileName = encodeURIComponent(originalFileName || file);
          const fileUrl = fileQuoteId ? 
            `/api/models/${fileQuoteId}/${encodedFileName}` : 
            `/api/models/${encodedFileName}`;
            
          console.log(`DEBUG: Generated fileUrl: ${fileUrl}`);
          
          return {
            id: file,
            fileName: originalFileName || file,
            partName: 'Part', // We don't have a good way to know this without metadata
            orderNumber: orderNumber,
            quoteId: fileQuoteId,
            fileType: fileExtension.toUpperCase(),
            uploadDate: new Date(), // Would be better to get actual file creation time
            fileSize: 0, // Would be better to get actual file size
            fileUrl: fileUrl,
            filePath: filePath
          };
          });
      }
      // If we have a quote ID, look for files matching that quote ID
      else if (quoteId) {
        console.log(`DEBUG: Fetching models by quote ID: ${quoteId}`);
        
        const files = await readdir(join(process.cwd(), 'storage', 'models'));
        console.log(`DEBUG: Found ${files.length} files in storage/models directory`);
        
        // Find files with the quote ID prefix (format is quoteId_filename)
        const matchingFiles = files
          .filter(file => file.startsWith(`${quoteId}_`));
          
        console.log(`DEBUG: Found ${matchingFiles.length} files matching quote ID ${quoteId}`);
        
        models = matchingFiles.map(file => {
          const fileExtension = file.split('.').pop() || '';
          const filePath = join(process.cwd(), 'storage', 'models', file);
          const fileName = file.split('_').slice(1).join('_'); // Remove quoteId_ prefix
          
          console.log(`DEBUG: Processing matched file: ${file}, extracted fileName: ${fileName}`);
          
          // Create a file URL that will work with our API route
          const encodedFileName = encodeURIComponent(fileName || file);
          const fileUrl = `/api/models/${quoteId}/${encodedFileName}`;
          console.log(`DEBUG: Generated fileUrl for quote: ${fileUrl}`);
          
          return {
            id: file,
            fileName: fileName || file,
            partName: 'Model for Quote', 
            orderNumber: 'Processing', // Don't have order number yet
            quoteId: quoteId,
            fileType: fileExtension.toUpperCase(),
            uploadDate: new Date(),
            fileSize: 0, // Would be better to get actual file size
            fileUrl: fileUrl,
            filePath: filePath
          };
          });
      }
      
      console.log(`DEBUG: Found ${models.length} models matching the criteria`);
      
      return NextResponse.json({
        success: true,
        models,
      });
    } catch (error) {
      console.error(`DEBUG: Error fetching models:`, error);
      // Return empty array on error
      return NextResponse.json({
        success: true,
        models: [],
      });
    }
  } catch (error) {
    console.error('Error getting models:', error);
    
    return NextResponse.json(
      { 
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error occurred' 
      },
      { status: 500 }
    );
  }
}