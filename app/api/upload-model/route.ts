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
    
    // Check file extension
    const fileName = file.name;
    const fileExtension = fileName.split('.').pop()?.toLowerCase() || '';
    console.log(`DEBUG: Received file with extension: ${fileExtension}`);
    
    // Check if it's a supported file type (STL, STEP, STP, OBJ)
    const supportedExtensions = ['stl', 'step', 'stp', 'obj'];
    if (!supportedExtensions.includes(fileExtension)) {
      console.error(`DEBUG: Unsupported file extension: ${fileExtension}`);
      return NextResponse.json(
        { success: false, error: `Unsupported file type: ${fileExtension}. Supported types are: ${supportedExtensions.join(', ')}` },
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
    
    // Check for FFF/FDM specific configuration
    const isFffConfigured = formData.get('fff_configured') === 'true';
    const material = formData.get('material') as string;
    const weightG = formData.get('weight_g') as string;
    const volumeCm3 = formData.get('volume_cm3') as string;
    
    // Log FFF configuration if available
    if (isFffConfigured) {
      console.log(`DEBUG: FFF configuration present for ${quoteId}`);
      console.log(`DEBUG: Material: ${material}, Weight: ${weightG}g, Volume: ${volumeCm3}cm³`);
      
      try {
        // Create or update a configuration file for this model
        // This will be used by the slicing service
        const configData = {
          quoteId,
          technology: technology || 'FDM',
          material: material || 'PLA',
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
        console.log(`DEBUG: Saved FFF configuration to ${configPath}`);
      } catch (configError) {
        console.error('DEBUG: Error saving FFF configuration:', configError);
        // Continue even if config save fails - we'll still upload the model
      }
    }
    
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
      'Uploaded Model', // Generic part name
      { // Add metadata including FFF configuration
        technology,
        isFffConfigured: isFffConfigured ? 'true' : 'false',
        material: material || '',
        weightG: weightG || '',
        volumeCm3: volumeCm3 || ''
      }
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
      storagePath: join(process.cwd(), 'storage', 'models'),
      fffConfigured: isFffConfigured
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