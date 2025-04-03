/**
 * API service for communicating with the manufacturing DFM API
 */

// API base URL - use environment variable or default to localhost:8000 for development
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';

/**
 * Interface for Quote request parameters
 */
export interface QuoteRequest {
  modelFile: File;
  process: 'CNC' | '3DP_SLA' | '3DP_SLS' | '3DP_FDM' | 'SHEET_METAL';
  material: string;
  finish: string;
  drawingFile?: File;
}

/**
 * Interface for DFM issue
 */
export interface DFMIssue {
  type: string;
  severity: string;
  description: string;
  location?: {
    x: number;
    y: number;
    z: number;
  };
}

/**
 * Interface for Quote response
 */
export interface QuoteResponse {
  success: boolean;
  quoteId: string;
  price?: number;
  currency?: string;
  leadTimeInDays?: number;
  manufacturingDetails?: {
    process: string;
    material: string;
    finish: string;
    boundingBox: {
      x: number;
      y: number;
      z: number;
    };
    volume: number;
    surfaceArea: number;
    // Enhanced fields from DFM analysis
    printabilityScore?: number;
    estimatedPrintTime?: string;
    materialUsage?: number;
    materialCost?: number;
    supportRequirements?: string;
  };
  dfmIssues?: DFMIssue[];
  message?: string;
  error?: string;
}

/**
 * Get a manufacturing quote
 * 
 * @param params Quote request parameters
 * @returns Quote response
 */
export async function getQuote(params: QuoteRequest): Promise<QuoteResponse> {
  const formData = new FormData();
  
  // Validate file input
  if (!params.modelFile) {
    console.error('No model file provided');
    return {
      success: false,
      quoteId: '',
      error: 'No model file provided. Please upload a .stl or .step file.'
    };
  }
  
  if (params.modelFile.size === 0) {
    console.error('Empty model file provided');
    return {
      success: false,
      quoteId: '',
      error: 'The model file is empty. Please upload a valid .stl or .step file.'
    };
  }
  
  // Log file details
  console.log('Uploading file:', params.modelFile.name, 'Size:', params.modelFile.size, 'bytes');
  
  try {
    // Use the exact field names expected by the Python backend
    formData.append('model_file', params.modelFile);
    formData.append('process', params.process);
    formData.append('material', params.material);
    formData.append('finish', params.finish);
    
    if (params.drawingFile) {
      formData.append('drawing_file', params.drawingFile);
    }
    
    // Log FormData creation
    console.log('Created FormData with:', 
      'process=', params.process, 
      'material=', params.material, 
      'finish=', params.finish,
      'modelFile=', params.modelFile.name
    );

    console.log(`Sending request to ${API_BASE_URL}/api/getQuote...`);
    
    // Use the Python API directly instead of the NextJS API route
    const response = await fetch(`${API_BASE_URL}/api/getQuote`, {
      method: 'POST',
      body: formData,
    });

    // For debugging
    console.log('Status:', response.status);
    console.log('Status Text:', response.statusText);
    
    // Check if the response is OK
    if (!response.ok) {
      try {
        const errorData = await response.json();
        console.error('API returned error:', errorData);
        return {
          success: false,
          quoteId: '',
          error: errorData.error || `API error: ${response.status} ${response.statusText}`
        };
      } catch (e) {
        // Handle case where error response isn't valid JSON
        const text = await response.text();
        console.error('Raw error response:', text);
        return {
          success: false,
          quoteId: '',
          error: `API error: ${response.status} ${response.statusText}. Raw response: ${text.substring(0, 100)}...`
        };
      }
    }

    // Parse response
    const data = await response.json();
    console.log('Successfully parsed response:', data);
    return data;
  } catch (error) {
    console.error('Error getting quote:', error);
    return {
      success: false,
      quoteId: '',
      error: error instanceof Error ? error.message : 'Unknown error occurred'
    };
  }
}

/**
 * Material options for each process - UPDATED to match backend expectations
 */
export const materialOptions = {
  'CNC': [
    { value: 'ALUMINUM_6061', label: 'Aluminum 6061' },
    { value: 'MILD_STEEL', label: 'Mild Steel' },
    { value: 'STAINLESS_STEEL_304', label: 'Stainless Steel 304' },
    { value: 'STAINLESS_STEEL_316', label: 'Stainless Steel 316' },
    { value: 'TITANIUM', label: 'Titanium' },
    { value: 'COPPER', label: 'Copper' },
    { value: 'BRASS', label: 'Brass' },
    { value: 'HDPE', label: 'HDPE' },
    { value: 'POM_ACETAL', label: 'POM (Acetal)' },
    { value: 'ABS', label: 'ABS' },
    { value: 'ACRYLIC', label: 'Acrylic' },
    { value: 'NYLON', label: 'Nylon' },
    { value: 'PEEK', label: 'PEEK' },
    { value: 'PC', label: 'Polycarbonate (PC)' },
  ],
  '3DP_SLA': [
    { value: 'STANDARD_RESIN', label: 'Standard Resin' },
  ],
  '3DP_SLS': [
    { value: 'NYLON_12_WHITE', label: 'Nylon 12 (White)' },
    { value: 'NYLON_12_BLACK', label: 'Nylon 12 (Black)' },
  ],
  '3DP_FDM': [
    { value: 'PLA', label: 'PLA' },
    { value: 'ABS', label: 'ABS' },
    { value: 'NYLON_12', label: 'Nylon 12' },
    { value: 'ASA', label: 'ASA' },
    { value: 'PETG', label: 'PETG' },
    { value: 'TPU', label: 'TPU' },
  ],
  'SHEET_METAL': [
    { value: 'ALUMINUM_6061', label: 'Aluminum 6061' },
    { value: 'MILD_STEEL', label: 'Mild Steel' },
    { value: 'STAINLESS_STEEL_304', label: 'Stainless Steel 304' },
    { value: 'STAINLESS_STEEL_316', label: 'Stainless Steel 316' },
    { value: 'TITANIUM', label: 'Titanium' },
    { value: 'COPPER', label: 'Copper' },
    { value: 'BRASS', label: 'Brass' },
  ],
};

/**
 * Finish options for each process - UPDATED to match backend expectations
 */
export const finishOptions = {
  'CNC': [
    { value: 'STANDARD', label: 'Standard' },
    { value: 'FINE', label: 'Fine' },
    { value: 'MIRROR', label: 'Mirror' },
  ],
  '3DP_SLA': [
    { value: 'STANDARD', label: 'Standard' },
    { value: 'FINE', label: 'Fine' },
  ],
  '3DP_SLS': [
    { value: 'STANDARD', label: 'Standard' },
  ],
  '3DP_FDM': [
    { value: 'STANDARD', label: 'Standard' },
    { value: 'FINE', label: 'Fine' },
  ],
  'SHEET_METAL': [
    { value: 'STANDARD', label: 'Standard' },
    { value: 'PAINTED', label: 'Painted' },
    { value: 'ANODIZED', label: 'Anodized' },
    { value: 'POWDER_COATED', label: 'Powder Coated' },
  ],
}; 