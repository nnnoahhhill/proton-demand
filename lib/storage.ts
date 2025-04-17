/**
 * 3D Model Storage Service
 */

export interface ModelFile {
  id: string;
  fileName: string;
  partName: string;
  orderNumber: string;
  fileType: string;
  uploadDate: Date;
  fileSize: number;
  fileUrl: string;
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
  metadata?: Record<string, any>
): Promise<ModelFile> {
  try {
    // Create a FormData object
    const formData = new FormData();
    formData.append('file', file);
    formData.append('partName', partName);
    formData.append('orderNumber', orderNumber);
    
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
 * Get models by order number
 */
export async function getModelsByOrderNumber(orderNumber: string): Promise<ModelFile[]> {
  try {
    const response = await fetch(`/api/models?orderNumber=${encodeURIComponent(orderNumber)}`);
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || 'Failed to retrieve models');
    }
    
    const data = await response.json();
    return data.models;
  } catch (error) {
    console.error('Error getting models by order number:', error);
    throw error;
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