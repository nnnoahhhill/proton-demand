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

// Map to track the current suffix for each quote session
const quoteSessionSuffixMap = new Map<string, string>();

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
 * Helper function to get the next suffix letter for a quote ID
 * This ensures parts in the same session get sequential suffixes (A, B, C, etc.)
 */
export function getNextSuffixForQuote(baseQuoteId: string): string {
  const currentSuffix = quoteSessionSuffixMap.get(baseQuoteId);
  
  if (!currentSuffix) {
    // First part for this quote session, start with 'A'
    quoteSessionSuffixMap.set(baseQuoteId, 'A');
    return 'A';
  }
  
  // Get the next letter in sequence
  const nextChar = String.fromCharCode(currentSuffix.charCodeAt(0) + 1);
  quoteSessionSuffixMap.set(baseQuoteId, nextChar);
  return nextChar;
}

/**
 * Extract the base quote ID from a suffixed quote ID
 * For example, Q-12345678-A returns Q-12345678
 */
export function getBaseQuoteId(suffixedQuoteId: string): string {
  const parts = suffixedQuoteId.split('-');
  if (parts.length <= 2) {
    // Not suffixed yet, return as is
    return suffixedQuoteId;
  }
  
  // Remove the last part (the suffix) and join the rest
  return parts.slice(0, -1).join('-');
}

/**
 * Create an order-specific folder for model storage
 * @param quoteId The quote ID (for backward compatibility)
 * @param orderId The order ID (payment intent ID) - preferred for folder naming
 */
export async function createOrderFolder(quoteId: string, orderId?: string): Promise<string> {
  try {
    // Extract base quote ID if this is a suffixed ID
    const baseQuoteId = getBaseQuoteId(quoteId);
    
    // Create a timestamp in PST format
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
      
    // Create folder name in the requested format - prioritize order ID if available
    const folderName = orderId 
      ? `${orderId}-${pstTimestamp}`  // New format with order ID (payment intent ID)
      : `${baseQuoteId}-${pstTimestamp}`; // Legacy format with quote ID
    
    const folderPath = path.join(MODELS_DIR, folderName);
    
    // Create the folder
    await mkdir(folderPath, { recursive: true });
    console.log(`DEBUG: Created order folder: ${folderPath}`);
    
    return folderPath;
  } catch (error) {
    console.error('DEBUG: Error creating order folder:', error);
    if (error instanceof Error) {
      console.error('DEBUG: Error stack:', error.stack);
    }
    return '';
  }
}

/**
 * Find the order folder for a given order ID or quote ID
 * @param quoteId The quote ID (for backward compatibility)
 * @param orderId The order ID (payment intent ID) - preferred for folder search
 */
export async function findOrderFolder(quoteId: string, orderId?: string): Promise<string> {
  try {
    console.log(`DEBUG: Finding order folder for quoteId: ${quoteId}, orderId: ${orderId || 'not provided'}`);
    
    // Extract base quote ID if this is a suffixed ID
    const baseQuoteId = getBaseQuoteId(quoteId);
    console.log(`DEBUG: Using base quote ID: ${baseQuoteId}`);
    
    // Read all directories in the models dir
    const items = await readdir(MODELS_DIR, { withFileTypes: true });
    const folders = items.filter(item => item.isDirectory());
    console.log(`DEBUG: Found ${folders.length} total folders in ${MODELS_DIR}`);
    
    // First try to find folders that match the order ID
    if (orderId) {
      console.log(`DEBUG: Looking for folders starting with order ID: ${orderId}-`);
      const orderIdFolders = folders.filter(
        folder => folder.name.startsWith(`${orderId}-`)
      );
      
      if (orderIdFolders.length > 0) {
        console.log(`DEBUG: Found ${orderIdFolders.length} folders matching order ID ${orderId}`);
        // Return the first matching folder (should only be one)
        const orderFolder = path.join(MODELS_DIR, orderIdFolders[0].name);
        console.log(`DEBUG: Using existing order folder: ${orderFolder}`);
        return orderFolder;
      }
    }
    
    // If no order ID folder found, try to find by quote ID (legacy)
    console.log(`DEBUG: Looking for folders starting with quote ID: ${baseQuoteId}-`);
    const quoteIdFolders = folders.filter(
      folder => folder.name.startsWith(`${baseQuoteId}-`) || 
               folder.name.includes(`-${baseQuoteId}-`) // Handle folders with embedded quote IDs
    );
    
    if (quoteIdFolders.length > 0) {
      console.log(`DEBUG: Found ${quoteIdFolders.length} folders matching quote ID ${baseQuoteId}`);
      // Return the first matching folder (should only be one)
      const quoteFolder = path.join(MODELS_DIR, quoteIdFolders[0].name);
      console.log(`DEBUG: Using existing quote folder: ${quoteFolder}`);
      return quoteFolder;
    }
    
    // No existing folder, create a new one with order ID if available
    console.log(`DEBUG: No existing folder found, creating new one`);
    return await createOrderFolder(quoteId, orderId);
  } catch (error) {
    console.error('DEBUG: Error finding order folder:', error);
    return '';
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
  metadata?: Record<string, string>,
  orderId?: string // Add payment intent ID parameter
): Promise<ModelFile | null> {
  try {
    console.log(`DEBUG: saveModelFileToFilesystem called - fileName: ${fileName}, quoteId: ${quoteId}, orderId: ${orderId || 'not provided'}`);
    
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

    // Extract the base quote ID for consistency
    const baseQuoteId = getBaseQuoteId(quoteId);
    
    // Get or create the suffix for this part
    let suffix = '';
    if (quoteId.includes('-') && quoteId.split('-').length > 2) {
      // Already has a suffix, use it
      suffix = quoteId.split('-').pop() || '';
    } else {
      // Generate a new suffix
      suffix = getNextSuffixForQuote(baseQuoteId);
    }

    // Create a suffixed quote ID 
    const suffixedQuoteId = `${baseQuoteId}-${suffix}`;
    console.log(`DEBUG: Using suffixed quote ID: ${suffixedQuoteId}`);
    
    // Find or create the order-specific folder, prioritizing order ID if available
    const orderFolderPath = await findOrderFolder(baseQuoteId, orderId);
    console.log(`DEBUG: Order folder path: ${orderFolderPath}`);
    
    // Create a filename with the suffixed quote ID
    const sanitizedFileName = fileName.replace(/[^a-zA-Z0-9._-]/g, '_');
    const storedFileName = `${suffixedQuoteId}_${sanitizedFileName}`;
    
    // Create the full paths for both the order folder and legacy storage
    const orderSpecificFilePath = path.join(orderFolderPath, storedFileName);
    const legacyStoredFilePath = path.join(MODELS_DIR, storedFileName);
    
    console.log(`DEBUG: Sanitized filename: ${sanitizedFileName}`);
    console.log(`DEBUG: Order-specific file path: ${orderSpecificFilePath}`);
    console.log(`DEBUG: Legacy stored file path: ${legacyStoredFilePath}`);

    // Create timestamp for metadata
    const timestamp = new Date().toISOString().replace(/[:.-]/g, '_');

    // Save file to both locations for compatibility
    try {
      // 1. Save to order-specific folder
      await writeFile(orderSpecificFilePath, fileBuffer);
      console.log(`DEBUG: File written to order-specific path`);
      
      // 2. Also save to legacy location for backward compatibility
      await writeFile(legacyStoredFilePath, fileBuffer);
      console.log(`DEBUG: File also written to legacy path`);
      
      // If metadata is provided, save it in both locations
      if (metadata && Object.keys(metadata).length > 0) {
        // Enhanced metadata with suffixed quote ID
        const metadataContent = {
          ...metadata,
          fileName,
          baseQuoteId,
          quoteId: suffixedQuoteId,
          suffix,
          orderNumber: orderNumber || '',
          orderId: orderId || '', // Store order ID in metadata
          partName: partName || '',
          timestamp,
          fileSize: fileBuffer.length,
          fileType: fileExtension,
          orderFolderPath
        };
        
        // Save metadata in the order folder
        const orderMetadataPath = `${orderSpecificFilePath}.metadata.json`;
        await writeFile(orderMetadataPath, JSON.stringify(metadataContent, null, 2));
        console.log(`DEBUG: Metadata saved to order folder: ${orderMetadataPath}`);
        
        // Also save metadata in legacy location
        const legacyMetadataPath = `${legacyStoredFilePath}.metadata.json`;
        await writeFile(legacyMetadataPath, JSON.stringify(metadataContent, null, 2));
        console.log(`DEBUG: Metadata also saved to legacy path: ${legacyMetadataPath}`);
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
      id: `${suffixedQuoteId}-${timestamp}`,
      fileName: fileName,
      partName: partName || 'Unnamed Part',
      orderNumber: orderNumber || 'Processing',
      quoteId: suffixedQuoteId,
      fileType: fileExtension,
      uploadDate: new Date(),
      fileSize: fileBuffer.length,
      fileUrl: `/api/models/${suffixedQuoteId}/${encodeURIComponent(fileName)}`,
      filePath: orderSpecificFilePath,
      metadata: {
        originalName: fileName,
        baseQuoteId,
        quoteId: suffixedQuoteId,
        suffix,
        orderId: orderId || '', // Include order ID in metadata
        timestamp: timestamp,
        orderFolderPath,
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
 * Get all model files for an order by quote ID
 * This returns all parts associated with a base quote ID
 */
export async function getAllOrderModels(quoteId: string): Promise<ModelFile[]> {
  try {
    // Extract base quote ID if this is a suffixed ID
    const baseQuoteId = getBaseQuoteId(quoteId);
    console.log(`DEBUG: Getting all models for order with base quote ID: ${baseQuoteId}`);
    
    // Try to find an order folder
    const orderFolder = await findOrderFolder(baseQuoteId);
    
    if (!orderFolder) {
      console.log(`DEBUG: No order folder found for quote ${baseQuoteId}`);
      return [];
    }
    
    // Read all files in the order folder
    const files = await readdir(orderFolder);
    
    // Filter out metadata files and only keep actual model files
    const modelFiles = files.filter(file => {
      // Skip metadata files
      if (file.endsWith('.metadata.json')) return false;
      
      // Keep files with valid extensions
      const ext = file.split('.').pop()?.toLowerCase() || '';
      return VALID_MODEL_TYPES.includes(ext);
    });
    
    console.log(`DEBUG: Found ${modelFiles.length} model files in order folder ${orderFolder}`);
    
    // Convert to ModelFile array
    const models: ModelFile[] = [];
    
    for (const file of modelFiles) {
      const filePath = path.join(orderFolder, file);
      // Use fs.stat instead of readdir with withFileTypes to get file size
      let fileSize = 0;
      try {
        const fs = await import('fs/promises');
        const stats = await fs.stat(filePath);
        fileSize = stats.size;
      } catch (statError) {
        console.error(`DEBUG: Error getting file stats for ${file}:`, statError);
      }
      
      // Try to find matching metadata
      const metadataPath = `${filePath}.metadata.json`;
      let metadata: Record<string, any> = {};
      
      try {
        if (existsSync(metadataPath)) {
          const fs = await import('fs/promises');
          const metadataContent = await fs.readFile(metadataPath, 'utf-8');
          metadata = JSON.parse(metadataContent);
        }
      } catch (metadataError) {
        console.error(`DEBUG: Error reading metadata for ${file}:`, metadataError);
      }
      
      // Extract suffix from either the metadata or parse from file name
      let suffixedQuoteId = baseQuoteId;
      let suffix = '';
      
      if (metadata.quoteId) {
        suffixedQuoteId = metadata.quoteId;
        suffix = metadata.suffix || '';
      } else {
        // Try to extract from filename
        const filenameParts = file.split('_')[0]; // The part before first underscore could be the ID
        if (filenameParts && filenameParts.includes('-')) {
          suffixedQuoteId = filenameParts;
          suffix = filenameParts.split('-').pop() || '';
        }
      }
      
      models.push({
        id: suffixedQuoteId,
        fileName: file,
        partName: metadata.partName || 'Part',
        orderNumber: metadata.orderNumber || 'Processing',
        quoteId: suffixedQuoteId,
        fileType: file.split('.').pop()?.toUpperCase() || '',
        uploadDate: new Date(metadata.timestamp ? metadata.timestamp.replace(/_/g, ':') : Date.now()),
        fileSize: fileSize || 0,
        fileUrl: `/api/models/${suffixedQuoteId}/${encodeURIComponent(file)}`,
        filePath,
        metadata: {
          ...metadata,
          suffix,
          baseQuoteId
        }
      });
    }
    
    return models;
  } catch (error) {
    console.error('DEBUG: Error getting all order models:', error);
    return [];
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
    console.log(`DEBUG: Looking for file with quoteId: ${quoteId}, fileName: ${fileName}`);
    const sanitizedFileName = fileName.replace(/[^a-zA-Z0-9._-]/g, '_');
    const storedFileName = `${quoteId}_${sanitizedFileName}`;
    const storedFilePath = path.join(MODELS_DIR, storedFileName);
    
    // First check if the exact path exists
    try {
      await access(storedFilePath, constants.F_OK);
      console.log(`DEBUG: Found exact file match: ${storedFilePath}`);
      return storedFilePath;
    } catch (exactErr) {
      console.log(`DEBUG: Exact file ${storedFilePath} not found, trying alternatives`);
    }
    
    // If exact match not found, try different search strategies
    try {
      // Read all files in the models directory
      const files = await readdir(MODELS_DIR);
      console.log(`DEBUG: Looking through ${files.length} files in ${MODELS_DIR}`);
      
      let matchingFile = null;

      // Search strategies in order of specificity:
      
      // 1. Look for exact quote ID prefix with the exact file name
      matchingFile = files.find(file => file === storedFileName);
      if (matchingFile) {
        console.log(`DEBUG: Found exact match for "${storedFileName}"`);
        return path.join(MODELS_DIR, matchingFile);
      }
      
      // 2. Look for files that start with the quote ID and end with the file name
      matchingFile = files.find(file => 
        file.startsWith(`${quoteId}_`) && 
        file.endsWith(sanitizedFileName)
      );
      if (matchingFile) {
        console.log(`DEBUG: Found match starting with "${quoteId}_" and ending with "${sanitizedFileName}"`);
        return path.join(MODELS_DIR, matchingFile);
      }
      
      // 3. Look for files that start with the quote ID
      matchingFile = files.find(file => file.startsWith(`${quoteId}_`));
      if (matchingFile) {
        console.log(`DEBUG: Found match with prefix "${quoteId}_"`);
        return path.join(MODELS_DIR, matchingFile);
      }
      
      // 4. Check in order-specific folders (look for folders that might match this quote ID)
      const items = await readdir(MODELS_DIR, { withFileTypes: true });
      const folders = items.filter(item => item.isDirectory());
      
      // Look for folders that contain this quote ID in their name
      const potentialFolders = folders.filter(folder => 
        folder.name.includes(quoteId) || 
        folder.name.startsWith('pi_') // Order folders start with payment intent ID
      );
      
      console.log(`DEBUG: Found ${potentialFolders.length} potential order folders`);
      
      // Search each potential folder for the file
      for (const folder of potentialFolders) {
        const folderPath = path.join(MODELS_DIR, folder.name);
        try {
          const folderFiles = await readdir(folderPath);
          console.log(`DEBUG: Searching in folder ${folderPath}`);
          
          // Look for an exact match on the name
          const folderMatch = folderFiles.find(file => file === sanitizedFileName || file === fileName);
          if (folderMatch) {
            console.log(`DEBUG: Found exact file match in folder: ${path.join(folderPath, folderMatch)}`);
            return path.join(folderPath, folderMatch);
          }
          
          // Look for files containing the quote ID or ending with the filename
          const partialMatch = folderFiles.find(file => 
            file.includes(quoteId) || 
            file.endsWith(sanitizedFileName) || 
            file.endsWith(fileName)
          );
          if (partialMatch) {
            console.log(`DEBUG: Found partial match in folder: ${path.join(folderPath, partialMatch)}`);
            return path.join(folderPath, partialMatch);
          }
        } catch (folderErr) {
          console.log(`DEBUG: Error reading folder ${folderPath}: ${folderErr}`);
        }
      }
      
      console.log(`DEBUG: No files found matching for quoteId ${quoteId} and fileName ${fileName}`);
      return null;
      
    } catch (readError) {
      console.error(`DEBUG: Error reading directory ${MODELS_DIR}:`, readError);
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