/**
 * Vercel Blob storage helper functions
 */
import { put, list } from '@vercel/blob';
import type { PutBlobResult, ListBlobResultBlob } from '@vercel/blob';

/**
 * Store a file in Vercel Blob
 * @param file The file to store
 * @param path The path to store the file at (e.g. orders/123/model.stl)
 * @returns The URL of the stored file
 */
export async function storeFileInBlob(
  file: File | Buffer | ArrayBuffer | string,
  path: string
): Promise<string | null> {
  try {
    let buffer: Buffer | string;
    let contentType: string | undefined;

    if (file instanceof File) {
      buffer = Buffer.from(await file.arrayBuffer());
      contentType = file.type || undefined;
    } else if (file instanceof ArrayBuffer) {
      buffer = Buffer.from(file);
    } else if (Buffer.isBuffer(file)) {
      buffer = file;
    } else if (typeof file === 'string') {
      buffer = file;
      contentType = 'text/plain';
    } else {
      throw new Error('Invalid file type. Expected File, Buffer, ArrayBuffer, or string.');
    }

    console.log(`DEBUG: Uploading to Blob path: ${path}`);

    const blobResult = await put(path, buffer, {
      access: 'public',
      contentType,
    });

    console.log(`DEBUG: Uploaded to Blob. URL: ${blobResult.url}`);
    return blobResult.url;
  } catch (error) {
    console.error(`DEBUG: Error uploading to Blob path ${path}:`, error);
    return null;
  }
}

/**
 * Get a file from Vercel Blob
 * @param blobUrl The URL of the file to get
 * @returns The file content as a Buffer
 */
export async function getFileFromBlob(blobUrl: string): Promise<Buffer | null> {
  try {
    console.log(`DEBUG: Getting file from Blob URL: ${blobUrl}`);
    const response = await fetch(blobUrl);
    if (!response.ok) {
      console.error(`DEBUG: Failed to get file from Blob URL: ${blobUrl} - Status: ${response.status}`);
      return null;
    }
    const arrayBuffer = await response.arrayBuffer();
    const buffer = Buffer.from(arrayBuffer);
    console.log(`DEBUG: Got file from Blob. Size: ${buffer.length}`);
    return buffer;
  } catch (error) {
    console.error(`DEBUG: Error getting file from Blob URL ${blobUrl}:`, error);
    return null;
  }
}

/**
 * List files in Vercel Blob with a specific prefix
 * @param prefix The prefix to list files for
 * @returns Array of blob objects
 */
export async function listFilesInBlob(prefix: string): Promise<ListBlobResultBlob[]> {
  try {
    console.log(`DEBUG: Listing Blob files with prefix: ${prefix}`);
    const listResult = await list({ prefix });
    console.log(`DEBUG: Found ${listResult.blobs.length} files with prefix: ${prefix}`);
    return listResult.blobs;
  } catch (error) {
    console.error(`DEBUG: Error listing Blob files with prefix ${prefix}:`, error);
    return [];
  }
}