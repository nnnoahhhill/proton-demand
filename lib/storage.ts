/**
 * 3D Model Storage Service
 */

import { writeFile, mkdir, access, readdir } from 'fs/promises';
import { constants } from 'fs';
import path from 'path';
import { existsSync } from 'fs';

// Base storage directory - in production this should be a persistent storage path
// Use absolute path to ensure consistency across all parts of the application
// IMPORTANT: The backend Python code also looks in {projectRoot}/storage/models
const projectRoot = process.cwd();
const STORAGE_BASE_DIR = process.env.STORAGE_BASE_DIR || path.join(projectRoot, 'storage');
const MODELS_DIR = path.join(STORAGE_BASE_DIR, 'models');

// File types we accept for 3D models
const VALID_MODEL_TYPES = ['stl', 'step', 'stp', 'obj'];

/**
 * Initialize storage directories
 */
export async function initStorage() {
  try {
    console.log(`DEBUG: Initializing storage directories`);
    console.log(`DEBUG: Project root: ${projectRoot}`);
    console.log(`DEBUG: Storage base dir: ${STORAGE_BASE_DIR}`);
    console.log(`DEBUG: Models dir: ${MODELS_DIR}`);
    
    // Check if storage directory exists, create if not
    try {
      await access(STORAGE_BASE_DIR, constants.F_OK);
      console.log(`DEBUG: Base storage directory exists`);
    } catch (e) {
      console.log(`DEBUG: Creating base storage directory: ${STORAGE_BASE_DIR}`);
      await mkdir(STORAGE_BASE_DIR, { recursive: true });
    }

    // Check if models directory exists, create if not
    try {
      await access(MODELS_DIR, constants.F_OK);
      console.log(`DEBUG: Models directory exists`);
    } catch (e) {
      console.log(`DEBUG: Creating models directory: ${MODELS_DIR}`);
      await mkdir(MODELS_DIR, { recursive: true });
    }
    
    // Print storage directory tree for debugging
    console.log(`DEBUG: Storage directory structure:`);
    if (existsSync(STORAGE_BASE_DIR)) {
      try {
        const files = await readdir(STORAGE_BASE_DIR);
        console.log(`DEBUG: Files in ${STORAGE_BASE_DIR}: ${files.join(', ')}`);
        
        if (existsSync(MODELS_DIR)) {
          const modelFiles = await readdir(MODELS_DIR);
          console.log(`DEBUG: Files in ${MODELS_DIR}: ${modelFiles.length > 0 ? modelFiles.join(', ') : 'No files'}`);
        }
      } catch (readError) {
        console.error(`DEBUG: Error reading directory structure:`, readError);
      }
    }

    console.log(`DEBUG: Storage directories initialized successfully`);
    return true;
  } catch (error) {
    console.error('DEBUG: Error initializing storage:', error);
    if (error instanceof Error) {
      console.error('DEBUG: Error stack:', error.stack);
    }
    return false;
  }
}

export interface ModelFile {
  id: string;
  fileName: string;
  partName: string;
  orderNumber: string;
  quoteId?: string; // Added quoteId field
  fileType: string;
  uploadDate: Date;
  fileSize: number;
  fileUrl: string;
  filePath?: string; // Added for server-side file path
  thumbnailUrl?: string;
  metadata?: Record<string, any>;
}

/**
 * Upload a 3D model file to storage
 */
export async function uploadModelFile(
  file: File,
  partName: string,
  orderNumber: string,
  metadata?: Record<string, any>,
  quoteId?: string
): Promise<ModelFile> {
  try {
    // Create a FormData object
    const formData = new FormData();
    formData.append('file', file);
    formData.append('partName', partName);
    formData.append('orderNumber', orderNumber);
    
    if (quoteId) {
      formData.append('quoteId', quoteId);
    }
    
    if (metadata) {
      formData.append('metadata', JSON.stringify(metadata));
    }
    
    // Upload the file using our API endpoint
    const response = await fetch('/api/models', {
      method: 'POST',
      body: formData,
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || 'Failed to upload model');
    }
    
    const data = await response.json();
    return data.model;
  } catch (error) {
    console.error('Error uploading model file:', error);
    throw error;
  }
}

/**
 * Save a model file to server filesystem
 * This should only be called from server-side code (API routes)
 */
export async function saveModelFileToFilesystem(
  fileBuffer: Buffer,
  fileName: string,
  quoteId: string,
  orderNumber?: string,
  partName?: string,
  metadata?: Record<string, string>
): Promise<ModelFile | null> {
  try {
    console.log(`DEBUG: saveModelFileToFilesystem called - fileName: ${fileName}, quoteId: ${quoteId}`);
    
    // Initialize storage - make sure directories exist
    const storageInitialized = await initStorage();
    if (!storageInitialized) {
      console.error(`DEBUG: Failed to initialize storage directories`);
      throw new Error('Failed to initialize storage directories');
    }

    // Get file extension
    const fileExtension = fileName.split('.').pop()?.toLowerCase() || '';
    console.log(`DEBUG: File extension: ${fileExtension}`);
    
    // Check if file type is valid - supports STL, STEP, STP, OBJ
    // Make sure we're case-insensitive in our checks
    const validExtensions = [...VALID_MODEL_TYPES, 'stl', 'step', 'stp', 'obj'];
    const isValidType = validExtensions.includes(fileExtension.toLowerCase());
    
    if (!isValidType) {
      console.error(`DEBUG: Invalid file type: ${fileExtension}`);
      throw new Error(`Invalid file type: ${fileExtension}. Supported types: ${VALID_MODEL_TYPES.join(', ')}`);
    } else {
      console.log(`DEBUG: Valid file type detected: ${fileExtension}`);
    }

    // Create a filename with the quote ID
    const timestamp = new Date().toISOString().replace(/[:.-]/g, '_');
    const sanitizedFileName = fileName.replace(/[^a-zA-Z0-9._-]/g, '_');
    const storedFileName = `${quoteId}_${sanitizedFileName}`;
    const storedFilePath = path.join(MODELS_DIR, storedFileName);
    
    console.log(`DEBUG: Sanitized filename: ${sanitizedFileName}`);
    console.log(`DEBUG: Stored filename: ${storedFileName}`);
    console.log(`DEBUG: Full storage path: ${storedFilePath}`);
    console.log(`DEBUG: File buffer size: ${fileBuffer.length} bytes`);

    // Write file to disk
    try {
      console.log(`DEBUG: Writing file to disk: ${storedFilePath}`);
      await writeFile(storedFilePath, fileBuffer);
      console.log(`DEBUG: File written successfully`);
      
      // If FFF configuration or other metadata is provided, save it
      if (metadata && Object.keys(metadata).length > 0) {
        // Save metadata in a corresponding JSON file
        const metadataFileName = `${storedFileName}.metadata.json`;
        const metadataFilePath = path.join(MODELS_DIR, metadataFileName);
        
        console.log(`DEBUG: Saving metadata to: ${metadataFilePath}`);
        
        // Create the metadata file
        const metadataContent = {
          ...metadata,
          fileName,
          quoteId,
          orderNumber: orderNumber || '',
          partName: partName || '',
          timestamp,
          fileSize: fileBuffer.length,
          fileType: fileExtension,
        };
        
        await writeFile(metadataFilePath, JSON.stringify(metadataContent, null, 2));
        console.log(`DEBUG: Metadata saved successfully`);
      }
    } catch (writeError) {
      console.error(`DEBUG: Error writing file to disk:`, writeError);
      if (writeError instanceof Error) {
        console.error(`DEBUG: Error stack:`, writeError.stack);
      }
      throw writeError;
    }

    // Create metadata about the file
    console.log(`DEBUG: Creating file metadata`);
    const modelFile: ModelFile = {
      id: `${quoteId}-${timestamp}`,
      fileName: fileName,
      partName: partName || 'Unnamed Part',
      orderNumber: orderNumber || 'Processing',
      quoteId: quoteId,
      fileType: fileExtension,
      uploadDate: new Date(),
      fileSize: fileBuffer.length,
      fileUrl: `/api/models/${quoteId}/${encodeURIComponent(fileName)}`,
      filePath: storedFilePath,
      metadata: {
        originalName: fileName,
        quoteId: quoteId,
        timestamp: timestamp,
        ...metadata // Include any additional metadata passed in
      },
    };

    console.log(`DEBUG: Model file metadata created successfully`);
    return modelFile;
  } catch (error) {
    console.error('DEBUG: Error saving model file to filesystem:', error);
    if (error instanceof Error) {
      console.error('DEBUG: Error stack:', error.stack);
    }
    return null;
  }
}

/**
 * Get models by order number
 * This is a client-side function that calls the API
 */
export async function getModelsByOrderNumber(orderNumber: string): Promise<ModelFile[]> {
  try {
    console.log(`DEBUG: Getting models by order number: ${orderNumber}`);
    const response = await fetch(`/api/models?orderNumber=${encodeURIComponent(orderNumber)}`);
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || 'Failed to retrieve models');
    }
    
    const data = await response.json();
    console.log(`DEBUG: Found ${data.models.length} models for order ${orderNumber}`);
    return data.models;
  } catch (error) {
    console.error('Error getting models by order number:', error);
    throw error;
  }
}

/**
 * Get models by quote ID
 * This is a client-side function that calls the API
 */
export async function getModelsByQuoteId(quoteId: string): Promise<ModelFile[]> {
  try {
    console.log(`DEBUG: Getting models by quote ID: ${quoteId}`);
    const response = await fetch(`/api/models?quoteId=${encodeURIComponent(quoteId)}`);
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || 'Failed to retrieve models');
    }
    
    const data = await response.json();
    console.log(`DEBUG: Found ${data.models.length} models for quote ${quoteId}`);
    return data.models;
  } catch (error) {
    console.error('Error getting models by quote ID:', error);
    throw error;
  }
}

/**
 * Get models directly from filesystem by order number
 * This should only be called from server-side code
 */
export async function getModelFilesFromFilesystemByOrder(orderNumber: string): Promise<ModelFile[]> {
  try {
    console.log(`DEBUG: Getting models from filesystem by order number: ${orderNumber}`);
    
    // Ensure storage is initialized
    await initStorage();
    
    // Read all files in the models directory
    const allFiles = await readdir(MODELS_DIR);
    console.log(`DEBUG: Found ${allFiles.length} total files in models directory`);
    
    // We'll need to check metadata of files to match by order number
    // For now, this is a placeholder that would need to be enhanced
    
    const models: ModelFile[] = [];
    return models;
  } catch (error) {
    console.error('Error getting models from filesystem by order number:', error);
    return [];
  }
}

/**
 * Get file from filesystem by quote ID and file name
 * This should only be called from server-side code
 */
export async function getModelFileFromFilesystem(quoteId: string, fileName: string): Promise<string | null> {
  try {
    const sanitizedFileName = fileName.replace(/[^a-zA-Z0-9._-]/g, '_');
    const storedFileName = `${quoteId}_${sanitizedFileName}`;
    const storedFilePath = path.join(MODELS_DIR, storedFileName);
    
    // Check if file exists
    try {
      await access(storedFilePath, constants.F_OK);
      console.log(`DEBUG: Found exact file match: ${storedFilePath}`);
      return storedFilePath;
    } catch {
      // Try finding any file with the quote ID prefix
      try {
        const files = await readdir(MODELS_DIR);
        console.log(`DEBUG: Looking for files with prefix "${quoteId}_" among ${files.length} files in ${MODELS_DIR}`);
        
        const matchingFile = files.find(file => file.startsWith(`${quoteId}_`));
        
        if (matchingFile) {
          const matchPath = path.join(MODELS_DIR, matchingFile);
          console.log(`DEBUG: Found matching file with prefix: ${matchPath}`);
          return matchPath;
        }
        
        console.log(`DEBUG: No files found matching prefix "${quoteId}_" in ${MODELS_DIR}`);
      } catch (readError) {
        console.error(`DEBUG: Error reading directory ${MODELS_DIR}:`, readError);
      }
      
      return null;
    }
  } catch (error) {
    console.error('Error getting model file from filesystem:', error);
    return null;
  }
}

/**
 * Delete a model file
 */
export async function deleteModelFile(fileUrl: string): Promise<boolean> {
  try {
    const encodedUrl = encodeURIComponent(fileUrl);
    const response = await fetch(`/api/models/${encodedUrl}`, {
      method: 'DELETE',
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || 'Failed to delete model');
    }
    
    return true;
  } catch (error) {
    console.error('Error deleting model file:', error);
    throw error;
  }
}