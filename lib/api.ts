/**
 * API service for communicating with the manufacturing DFM API
 */

// API base URL - adjust this to your environment
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
  formData.append('model_file', params.modelFile);
  formData.append('process', params.process);
  formData.append('material', params.material);
  formData.append('finish', params.finish);
  
  if (params.drawingFile) {
    formData.append('drawing_file', params.drawingFile);
  }

  try {
    const response = await fetch(`${API_BASE_URL}/api/getQuote`, {
      method: 'POST',
      body: formData,
    });

    // Check if the response is OK
    if (!response.ok) {
      const errorData = await response.json();
      return {
        success: false,
        quoteId: '',
        error: errorData.error || `API error: ${response.status} ${response.statusText}`
      };
    }

    // Parse the response
    const data = await response.json();
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
 * Material options for each process
 */
export const materialOptions = {
  'CNC': [
    { value: 'aluminum_6061', label: 'Aluminum 6061' },
    { value: 'mild_steel', label: 'Mild Steel' },
    { value: 'stainless_304', label: 'Stainless Steel 304' },
    { value: 'stainless_316', label: 'Stainless Steel 316' },
    { value: 'titanium', label: 'Titanium' },
    { value: 'copper', label: 'Copper' },
    { value: 'brass', label: 'Brass' },
    { value: 'hdpe', label: 'HDPE' },
    { value: 'pom_acetal', label: 'POM (Acetal)' },
    { value: 'abs', label: 'ABS' },
    { value: 'acrylic', label: 'Acrylic' },
    { value: 'nylon', label: 'Nylon' },
    { value: 'peek', label: 'PEEK' },
    { value: 'pc', label: 'Polycarbonate (PC)' },
  ],
  '3DP_SLA': [
    { value: 'resin_standard', label: 'Standard Resin' },
  ],
  '3DP_SLS': [
    { value: 'nylon_12_white', label: 'Nylon 12 (White)' },
    { value: 'nylon_12_black', label: 'Nylon 12 (Black)' },
  ],
  '3DP_FDM': [
    { value: 'pla', label: 'PLA' },
    { value: 'abs', label: 'ABS' },
    { value: 'nylon_12', label: 'Nylon 12' },
    { value: 'asa', label: 'ASA' },
    { value: 'petg', label: 'PETG' },
    { value: 'tpu', label: 'TPU' },
  ],
  'SHEET_METAL': [
    { value: 'aluminum_6061', label: 'Aluminum 6061' },
    { value: 'mild_steel', label: 'Mild Steel' },
    { value: 'stainless_304', label: 'Stainless Steel 304' },
    { value: 'stainless_316', label: 'Stainless Steel 316' },
    { value: 'titanium', label: 'Titanium' },
    { value: 'copper', label: 'Copper' },
    { value: 'brass', label: 'Brass' },
  ],
};

/**
 * Finish options for each process
 */
export const finishOptions = {
  'CNC': [
    { value: 'standard', label: 'Standard' },
    { value: 'fine', label: 'Fine' },
    { value: 'mirror', label: 'Mirror' },
  ],
  '3DP_SLA': [
    { value: 'standard', label: 'Standard' },
    { value: 'fine', label: 'Fine' },
  ],
  '3DP_SLS': [
    { value: 'standard', label: 'Standard' },
  ],
  '3DP_FDM': [
    { value: 'standard', label: 'Standard' },
    { value: 'fine', label: 'Fine' },
  ],
  'SHEET_METAL': [
    { value: 'standard', label: 'Standard' },
    { value: 'painted', label: 'Painted' },
    { value: 'anodized', label: 'Anodized' },
    { value: 'powder_coated', label: 'Powder Coated' },
  ],
}; 