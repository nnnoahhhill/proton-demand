import { NextRequest, NextResponse } from 'next/server';
import { saveModelFileToFilesystem, initStorage } from '@/lib/storage';
import { join } from 'path';

/**
 * API endpoint to upload a model file.
 * This is a simpler version of the model file storage
 * that happens during the quote process, but allows us
 * to store the model immediately after quote generation.
 */
export async function POST(req: NextRequest) {
  console.log('DEBUG: POST /api/upload-model called');
  
  try {
    // Initialize storage
    await initStorage();
    
    // Parse the multipart form data
    const formData = await req.formData();
    
    // Get the model file
    const file = formData.get('file') as File;
    if (!file) {
      console.error('DEBUG: No file found in request');
      return NextResponse.json(
        { success: false, error: 'No file found in request' },
        { status: 400 }
      );
    }
    
    // Get the quote ID
    const quoteId = formData.get('quoteId') as string;
    if (!quoteId) {
      console.error('DEBUG: No quoteId found in request');
      return NextResponse.json(
        { success: false, error: 'Quote ID is required' },
        { status: 400 }
      );
    }
    
    // Get the technology (optional)
    const technology = formData.get('technology') as string;
    
    console.log(`DEBUG: Processing upload for file: ${file.name}, quoteId: ${quoteId}, technology: ${technology || 'unknown'}`);
    console.log(`DEBUG: File size: ${file.size} bytes, type: ${file.type}`);
    
    // Convert file to buffer
    const buffer = Buffer.from(await file.arrayBuffer());
    console.log(`DEBUG: Converted file to buffer: ${buffer.length} bytes`);
    
    // Save the file to the filesystem
    const savedFile = await saveModelFileToFilesystem(
      buffer,
      file.name,
      quoteId,
      undefined, // No order number yet
      'Uploaded Model' // Generic part name
    );
    
    if (!savedFile) {
      console.error('DEBUG: Failed to save model file');
      return NextResponse.json(
        { success: false, error: 'Failed to save model file' },
        { status: 500 }
      );
    }
    
    console.log(`DEBUG: Successfully saved model file: ${savedFile.filePath}`);
    
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
      storagePath: join(process.cwd(), 'storage', 'models')
    };
    
    console.log(`DEBUG: Returning upload success response: ${JSON.stringify(response)}`);
    return NextResponse.json(response);
    
  } catch (error) {
    console.error('DEBUG: Error uploading model file:', error);
    
    return NextResponse.json(
      { 
        success: false, 
        error: error instanceof Error ? error.message : 'Unknown error occurred' 
      },
      { status: 500 }
    );
  }
}