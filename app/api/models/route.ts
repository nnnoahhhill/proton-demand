import { NextRequest, NextResponse } from 'next/server';
import { join } from 'path';
import { writeFile, mkdir, readdir } from 'fs/promises';

// Base directory for storing models
const BASE_DIR = process.env.MODEL_STORAGE_DIR || './public/models';

export async function POST(req: NextRequest) {
  try {
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
    
    // Ensure the order directory exists
    const orderDir = join(BASE_DIR, orderNumber);
    await mkdir(orderDir, { recursive: true });
    
    // Create a safe filename
    const fileExtension = file.name.split('.').pop() || '';
    const safePartName = partName.replace(/[^a-zA-Z0-9]/g, '_');
    const filename = `${safePartName}_${Date.now()}.${fileExtension}`;
    const filePath = join(orderDir, filename);
    
    // Save the file
    const buffer = Buffer.from(await file.arrayBuffer());
    await writeFile(filePath, buffer);
    
    // Create the public URL
    const fileUrl = `/models/${orderNumber}/${filename}`;
    
    // Create metadata file if provided
    const metadata = metadataJson ? JSON.parse(metadataJson) : {};
    
    if (Object.keys(metadata).length > 0) {
      const metadataPath = join(orderDir, `${filename}.meta.json`);
      await writeFile(metadataPath, JSON.stringify(metadata, null, 2));
    }
    
    // Extract file type
    const fileType = fileExtension.toUpperCase();
    
    // Create model data
    const modelData = {
      id: fileUrl,
      fileName: file.name,
      partName,
      orderNumber,
      fileType,
      uploadDate: new Date(),
      fileSize: file.size,
      fileUrl,
      metadata,
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
    
    if (!orderNumber) {
      return NextResponse.json(
        { error: 'Order number is required' },
        { status: 400 }
      );
    }
    
    // Get all files in the order directory
    const orderDir = join(BASE_DIR, orderNumber);
    
    try {
      const files = await readdir(orderDir);
      
      // Filter out metadata files and only include model files
      const modelFiles = files.filter(file => !file.endsWith('.meta.json'));
      
      // Create model data for each file
      const models = modelFiles.map(file => {
        const [partName] = file.split('_');
        const fileExtension = file.split('.').pop() || '';
        const fileUrl = `/models/${orderNumber}/${file}`;
        
        // Basic file stats (in a real implementation, you would get actual file size)
        return {
          id: fileUrl,
          fileName: file,
          partName,
          orderNumber,
          fileType: fileExtension.toUpperCase(),
          uploadDate: new Date(), // In a real implementation, use file stats
          fileSize: 0, // In a real implementation, use file stats
          fileUrl,
        };
      });
      
      return NextResponse.json({
        success: true,
        models,
      });
    } catch (error) {
      // If directory doesn't exist, return empty array
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