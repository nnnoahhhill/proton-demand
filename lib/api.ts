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
  process: '3D Printing' | 'CNC Machining' | 'Sheet Metal';
  material: string;
  finish: string;
  drawingFile?: File;
}

/**
 * Interface for DFM issue
 */
export interface DFMIssue {
  // Match backend core/common_types.py DFMIssue model
  issue_type: string; // Should ideally be the DFMIssueType enum, but string is simpler for now
  level: string; // Should ideally be the DFMLevel enum
  message: string;
  recommendation?: string;
  visualization_hint?: any; 
  details?: { [key: string]: any }; // Matches backend details dict
}

/**
 * Interface for Material Info (matching backend)
 */
export interface MaterialInfo {
  id: string;
  name: string;
  process: string; // Matches ManufacturingProcess value e.g., "3D Printing"
  technology?: string;
  density_g_cm3: number;
  cost_per_kg?: number;
  cost_per_liter?: number;
  currency?: string; // Added currency here for frontend display
  slicer_profile_id?: string; // Added for potential use
}

/**
 * Interface for Quote response (matching backend QuoteResult)
 */
export interface QuoteResponse {
  success: boolean;
  quote_id: string; // Changed from quoteId
  file_name?: string; // Added from backend
  process?: string; // Added from backend (matches ManufacturingProcess value)
  technology?: string; // Added from backend
  material_info?: MaterialInfo; // Changed from manufacturingDetails, uses new MaterialInfo interface
  dfm_report?: { // Changed from dfmIssues, matches backend DFMReport structure
      status: string; // e.g., "Pass", "Warning", "Fail"
      issues: DFMIssue[];
      analysis_time_sec?: number;
  };
  cost_estimate?: { // Added from backend
      material_id: string;
      material_volume_cm3: number;
      support_volume_cm3?: number;
      total_volume_cm3: number;
      material_weight_g: number;
      material_cost: number;
      process_time_seconds: number;
      base_cost: number;
      cost_analysis_time_sec: number;
  };
  customer_price?: number; // Changed from price
  estimated_process_time_str?: string; // Added from backend
  processing_time_sec?: number; // Added from backend
  error_message?: string; // Changed from error/message
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
      quote_id: '',
      error_message: 'No model file provided. Please upload a .stl or .step file.'
    };
  }
  
  if (params.modelFile.size === 0) {
    console.error('Empty model file provided');
    return {
      success: false,
      quote_id: '',
      error_message: 'The model file is empty. Please upload a valid .stl or .step file.'
    };
  }
  
  // Log file details
  console.log('Uploading file:', params.modelFile.name, 'Size:', params.modelFile.size, 'bytes');
  
  try {
    // Use the exact field names expected by the Python backend
    formData.append('model_file', params.modelFile);
    formData.append('process', params.process);
    formData.append('material_id', params.material);
    
    if (params.drawingFile) {
      formData.append('drawing_file', params.drawingFile);
    }
    
    // Log FormData creation
    console.log('Created FormData with:', 
      'process=', params.process, 
      'material_id=', params.material,
      'modelFile=', params.modelFile.name
    );

    // Corrected endpoint path
    const endpointUrl = `${API_BASE_URL}/quote`; 
    console.log(`Sending request to ${endpointUrl}...`);
    
    // Use the Python API directly with a timeout controller
    const controller = new AbortController();
    // Increase timeout to 120 seconds for larger files
    const timeoutId = setTimeout(() => controller.abort(), 120000); 
    
    try {
      const response = await fetch(endpointUrl, {
        method: 'POST',
        body: formData,
        signal: controller.signal,
      });
      
      clearTimeout(timeoutId);

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
            quote_id: '',
            error_message: errorData.error || `API error: ${response.status} ${response.statusText}`
          };
        } catch (e) {
          // Handle case where error response isn't valid JSON
          const text = await response.text();
          console.error('Raw error response:', text);
          return {
            success: false,
            quote_id: '',
            error_message: `API error: ${response.status} ${response.statusText}. Raw response: ${text.substring(0, 100)}...`
          };
        }
      }

      // Parse response
      const data = await response.json();
      console.log('Successfully parsed response:', data);
      return data;
    } catch (fetchError: any) {
      clearTimeout(timeoutId);
      if (fetchError.name === 'AbortError') {
        console.error('Request timed out after 120 seconds');
        return {
          success: false,
          quote_id: '',
          error_message: 'Request timed out. The server might be busy or unavailable.'
        };
      }
      throw fetchError; // Re-throw for the outer catch
    }
  } catch (error) {
    console.error('Error getting quote:', error);
    return {
      success: false,
      quote_id: '',
      error_message: error instanceof Error 
        ? `${error.name}: ${error.message}` 
        : 'Unknown error occurred'
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

/**
 * Interface for Stripe Checkout Session request
 */
export interface CreateCheckoutSessionRequest {
  item_name: string;
  price: number;
  currency?: string;
  quantity?: number;
  quote_id?: string;
  file_name?: string;
}

/**
 * Interface for Stripe Checkout Session response
 */
export interface CreateCheckoutSessionResponse {
  sessionId?: string;
  url?: string;
  error?: string;
}

/**
 * Create a Stripe Checkout Session
 */
export async function createCheckoutSession(
  params: CreateCheckoutSessionRequest
): Promise<CreateCheckoutSessionResponse> {
  console.log("Requesting Stripe Checkout session with params:", params);
  try {
    const response = await fetch(`${API_BASE_URL}/create-checkout-session`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(params),
    });

    console.log('Checkout Session API Status:', response.status);

    if (!response.ok) {
      try {
        const errorData = await response.json();
        console.error('Checkout Session API returned error:', errorData);
        return { error: errorData.detail || `API error: ${response.status}` };
      } catch (e) {
        const text = await response.text();
        console.error('Raw Checkout Session error response:', text);
        return { error: `API error: ${response.status}. Raw: ${text.substring(0, 100)}...` };
      }
    }

    const data = await response.json();
    console.log('Received Checkout Session data:', data);
    if (!data.sessionId) {
        return { error: 'Missing sessionId in API response' };
    }
    return { sessionId: data.sessionId, url: data.url };

  } catch (error) {
    console.error('Error creating Stripe Checkout session:', error);
    return {
      error: error instanceof Error ? error.message : 'Unknown client-side error occurred'
    };
  }
}

/**
 * --- Payment Intent Integration --- 
 */

// Interface definitions copied from user's previous code
export interface SimpleCartItem { // Renamed to avoid conflict if CartItem exists elsewhere
  id: string;
  name: string;
  quantity: number;
  price: number; // Price per item
}

export interface CreatePaymentIntentRequest {
  items: SimpleCartItem[];
  currency?: string;
  customer_email?: string;
  // Add other fields matching backend Pydantic model PaymentIntentRequest if needed
  metadata?: Record<string, string>;
}

export interface PaymentIntentResponse {
  clientSecret?: string;
  paymentIntentId?: string;
  amount?: number;
  currency?: string;
  error?: string;
}

/**
 * Create a Stripe Payment Intent
 */
export async function createPaymentIntent(
  params: CreatePaymentIntentRequest
): Promise<PaymentIntentResponse> {
  console.log("Requesting Payment Intent with params:", params);
  try {
    // Ensure currency is lowercase if provided
    const bodyParams = {
       ...params,
       currency: params.currency?.toLowerCase() || 'usd'
    };

    const response = await fetch(`${API_BASE_URL}/create-payment-intent`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(bodyParams),
    });

    console.log('Payment Intent API Status:', response.status);

    if (!response.ok) {
      try {
        const errorData = await response.json();
        console.error('Payment Intent API returned error:', errorData);
        return { error: errorData.detail || `API error: ${response.status}` };
      } catch (e) {
        const text = await response.text();
        console.error('Raw Payment Intent error response:', text);
        return { error: `API error: ${response.status}. Raw: ${text.substring(0, 100)}...` };
      }
    }

    const data: PaymentIntentResponse = await response.json();
    console.log('Received Payment Intent data:', data);
    if (!data.clientSecret) {
        return { error: 'Missing clientSecret in API response' };
    }
    return data; // Contains clientSecret, paymentIntentId, amount, currency

  } catch (error) {
    console.error('Client-side error creating Payment Intent:', error);
    return {
      error: error instanceof Error ? error.message : 'Unknown client-side error occurred'
    };
  }
}

// -- Existing Slack Notification function (if applicable) --
// export async function sendOrderNotification(...) { ... } 
// Note: This should likely be triggered server-side via webhook now, not from client 