import { NextRequest, NextResponse } from 'next/server';
import { unlink } from 'fs/promises';
import { join } from 'path';

// Base directory for storing models
const BASE_DIR = process.env.MODEL_STORAGE_DIR || './public/models';

export async function DELETE(
  req: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const fileUrl = decodeURIComponent(params.id);
    
    if (!fileUrl) {
      return NextResponse.json(
        { error: 'File URL is required' },
        { status: 400 }
      );
    }
    
    // Extract the relative path from the URL
    // fileUrl format is typically /models/orderNumber/filename
    const relativePath = fileUrl.startsWith('/') ? fileUrl.substring(1) : fileUrl;
    const filePath = join(process.cwd(), 'public', relativePath);
    
    // Delete the file
    await unlink(filePath);
    
    // Try to delete the metadata file if it exists
    try {
      await unlink(`${filePath}.meta.json`);
    } catch (error) {
      // Ignore errors if metadata file doesn't exist
    }
    
    return NextResponse.json({
      success: true,
      message: 'Model deleted successfully',
    });
  } catch (error) {
    console.error('Error deleting model:', error);
    
    return NextResponse.json(
      { 
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error occurred' 
      },
      { status: 500 }
    );
  }
}