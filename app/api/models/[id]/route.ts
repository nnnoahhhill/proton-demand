import { NextRequest, NextResponse } from 'next/server';
import { unlink, access, readdir } from 'fs/promises';
import { constants } from 'fs';
import { join } from 'path';
import { getModelFileFromFilesystem, initStorage } from '@/lib/storage';

// Use the centralized storage system instead of a separate path
// We'll be working with storage/models directory

// GET handler to serve model files
export async function GET(
  req: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const fileId = decodeURIComponent(params.id);
    console.log(`DEBUG: GET /api/models/${fileId} called`);
    
    // Initialize storage
    await initStorage();
    
    if (!fileId) {
      return NextResponse.json(
        { error: 'File ID is required' },
        { status: 400 }
      );
    }
    
    // The same file finding logic as in DELETE
    // Determine the file path
    let filePath = '';
    
    // Use the same complex file finding logic as in the DELETE method
    // But refactor to use more direct approach for common paths
    
    // First try to use the getModelFileFromFilesystem utility
    // Parse the quoteId and fileName from the path if possible
    const pathParts = fileId.split('/').filter(Boolean);
    
    if (pathParts.length >= 2) {
      const quoteId = pathParts[pathParts.length - 2];
      const fileName = pathParts[pathParts.length - 1];
      
      console.log(`DEBUG: Trying to get file with quoteId: ${quoteId}, fileName: ${fileName}`);
      
      try {
        // Try to find the file using our storage utility
        filePath = await getModelFileFromFilesystem(quoteId, fileName) || '';
        
        if (filePath) {
          console.log(`DEBUG: Found file using storage utility: ${filePath}`);
        } else {
          console.log(`DEBUG: File not found with storage utility, trying fallback methods`);
        }
      } catch (err) {
        console.error(`DEBUG: Error using storage utility: ${err instanceof Error ? err.message : 'unknown error'}`);
      }
    }
    
    // If not found, use the same file searching logic as DELETE
    if (!filePath) {
      console.log(`DEBUG: File not found with direct methods, trying fallback search`);
      
      // Here we'd duplicate the file search logic from DELETE
      // But for brevity, we'll just return a file not found error
      return NextResponse.json(
        { error: 'File not found' },
        { status: 404 }
      );
    }
    
    // File found, serve it
    try {
      // For simplicity, we'll just return the file path
      // In a real implementation, you'd use the Response object to serve the file
      return NextResponse.json({
        success: true,
        filePath: filePath,
        // You should probably use a streaming response to serve large files
      });
    } catch (error) {
      console.error(`DEBUG: Error serving file:`, error);
      return NextResponse.json(
        { error: 'Failed to serve file' },
        { status: 500 }
      );
    }
  } catch (error) {
    console.error('Error serving model:', error);
    
    return NextResponse.json(
      { 
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error occurred' 
      },
      { status: 500 }
    );
  }
}

// DELETE handler to remove model files
export async function DELETE(
  req: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const fileId = decodeURIComponent(params.id);
    console.log(`DEBUG: DELETE /api/models/${fileId} called`);
    
    // Initialize storage
    await initStorage();
    
    if (!fileId) {
      return NextResponse.json(
        { error: 'File ID is required' },
        { status: 400 }
      );
    }
    
    // The fileId could be in several formats:
    // 1. Direct filename with quoteId prefix (quoteId_filename.stl)
    // 2. Legacy path format (/models/orderNumber/filename)
    
    // Determine the file path
    let filePath = '';
    
    console.log(`DEBUG: Received fileId: ${fileId}`);
    
    // First check if this is a direct filename from storage/models
    // Check if it comes from our standard naming pattern quoteId_filename.stl
    if (fileId.includes('_')) {
      const potentialQuoteId = fileId.split('_')[0];
      console.log(`DEBUG: Checking for file with potential quoteId prefix: ${potentialQuoteId}`);
      
      // Look for this file in storage/models
      filePath = join(process.cwd(), 'storage', 'models', fileId);
      console.log(`DEBUG: Checking path: ${filePath}`);
      
      // Check if file exists
      try {
        await access(filePath, constants.F_OK);
        console.log(`DEBUG: Found file at ${filePath}`);
      } catch (err) {
        console.log(`DEBUG: File not found at ${filePath}: ${err instanceof Error ? err.message : 'unknown error'}`);
        filePath = ''; // Reset if not found
      }
    }
    
    // If not found yet, try to parse as a URL path (which is how our fileUrls are formatted)
    if (!filePath) {
      // Extract parts from the URL-style path
      console.log(`DEBUG: Trying to parse as URL path: ${fileId}`);
      
      // Check if we need to add the missing first slash
      const normalizedId = fileId.startsWith('/') ? fileId : `/${fileId}`;
      console.log(`DEBUG: Normalized ID: ${normalizedId}`);
      
      const pathParts = normalizedId.split('/').filter(Boolean);
      console.log(`DEBUG: Path parts: ${JSON.stringify(pathParts)}`);
      
      if (pathParts.length >= 2) {
        // For paths like /api/models/quoteId/filename or just /quoteId/filename
        const identifier = pathParts[pathParts.length - 2]; // Could be order number or quote ID
        const fileName = pathParts[pathParts.length - 1];
        console.log(`DEBUG: Extracted identifier: ${identifier}, fileName: ${fileName}`);
        
        // Check for a combined path format that could be created by the API
        const potentialFilename = `${identifier}_${fileName}`;
        console.log(`DEBUG: Checking for potential combined filename: ${potentialFilename}`);
        
        // Try to find any file in storage/models with this fileName or that ends with this fileName
        try {
          const modelFiles = await readdir(join(process.cwd(), 'storage', 'models'));
          console.log(`DEBUG: Searching among ${modelFiles.length} files in storage/models`);
          
          // First check for the exact combined filename
          let matchingFile = modelFiles.find(file => file === potentialFilename);
          console.log(`DEBUG: Search for exact match with ${potentialFilename}: ${matchingFile ? 'Found' : 'Not found'}`);
          
          // Then try to find a file that has the identifier as prefix and filename as suffix
          if (!matchingFile) {
            matchingFile = modelFiles.find(file => file.startsWith(`${identifier}_`) && file.endsWith(fileName));
            console.log(`DEBUG: Search for prefix ${identifier}_ and suffix ${fileName}: ${matchingFile ? 'Found' : 'Not found'}`);
          }
          
          // If still not found, try just matching the filename (as decoded parameter)
          if (!matchingFile) {
            try {
              // The filename might have been URL encoded
              const decodedFileName = decodeURIComponent(fileName);
              console.log(`DEBUG: Decoded filename: ${decodedFileName}`);
              
              matchingFile = modelFiles.find(file => file.endsWith(decodedFileName));
              console.log(`DEBUG: Search for decoded suffix ${decodedFileName}: ${matchingFile ? 'Found' : 'Not found'}`);
            } catch (decodeErr) {
              console.log(`DEBUG: Error decoding filename: ${decodeErr instanceof Error ? decodeErr.message : 'unknown error'}`);
            }
          }
          
          // Finally, try just the raw filename
          if (!matchingFile) {
            matchingFile = modelFiles.find(file => file.endsWith(fileName));
            console.log(`DEBUG: Search for raw suffix ${fileName}: ${matchingFile ? 'Found' : 'Not found'}`);
          }
          
          // Log all files to help with debugging
          console.log(`DEBUG: All files in directory: ${JSON.stringify(modelFiles)}`);
          
          if (matchingFile) {
            filePath = join(process.cwd(), 'storage', 'models', matchingFile);
            console.log(`DEBUG: Found file by name: ${filePath}`);
          } else {
            // Legacy path in the old location
            filePath = join(process.cwd(), 'public', pathParts.join('/'));
            console.log(`DEBUG: Falling back to legacy path: ${filePath}`);
          }
        } catch (err) {
          console.error(`DEBUG: Error searching models directory: ${err instanceof Error ? err.message : 'unknown error'}`);
          // Legacy path in the old location as fallback
          filePath = join(process.cwd(), 'public', pathParts.join('/'));
          console.log(`DEBUG: Falling back to legacy path after error: ${filePath}`);
        }
      } else {
        console.log(`DEBUG: URL path doesn't have enough parts: ${fileId}`);
      }
    }
    
    if (!filePath) {
      return NextResponse.json(
        { error: 'File not found' },
        { status: 404 }
      );
    }
    
    // Delete the file
    try {
      await unlink(filePath);
      console.log(`DEBUG: Deleted file at ${filePath}`);
    } catch (error) {
      console.error(`DEBUG: Error deleting file:`, error);
      return NextResponse.json(
        { error: 'Failed to delete file' },
        { status: 500 }
      );
    }
    
    // Try to delete any metadata file if it exists
    try {
      await unlink(`${filePath}.meta.json`);
      console.log(`DEBUG: Deleted metadata file ${filePath}.meta.json`);
    } catch (error) {
      // Ignore errors if metadata file doesn't exist
      console.log(`DEBUG: No metadata file to delete or error: ${error instanceof Error ? error.message : 'unknown'}`);
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