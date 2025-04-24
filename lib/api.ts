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
  technology?: 'FDM' | 'SLA' | 'SLS'; // Added for 3D printing technologies
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
    
    // Add technology if provided
    if (params.technology) {
      formData.append('technology', params.technology);
    }
    
    if (params.drawingFile) {
      formData.append('drawing_file', params.drawingFile);
    }
    
    // Log FormData creation
    console.log('Created FormData with:', 
      'process=', params.process, 
      'technology=', params.technology || 'not specified',
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
  shipping_cost?: number;
  material?: string;
  quantity?: string;
  items?: Array<{
    id: string;
    name: string;
    price: number;
    quantity: number;
    description?: string;
    material?: string;
    process?: string;
    technology?: string;
  }>;
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
  // CRITICAL TERMINAL LOGGING
  console.log('\n===== API SHIPPING COST DEBUG (TERMINAL) =====');
  console.log('RECEIVED SHIPPING COST:', params.shipping_cost);
  console.log('SHIPPING COST TYPE:', typeof params.shipping_cost);
  console.log('SHIPPING COST AS NUMBER:', Number(params.shipping_cost));
  
  console.log("Requesting Stripe Checkout session with params:", params);
  
  // Add detailed shipping cost log
  console.log(`\n
🚚 🚚 🚚 SHIPPING COST DEBUG 🚚 🚚 🚚
Request includes shipping_cost: $${params.shipping_cost?.toFixed(2) || '0.00'}
\n`);
  
  // Ensure shipping cost is a valid number and convert to cents for Stripe
  const shippingCostCents = Math.round(Number(params.shipping_cost || 0) * 100);
  console.log('SHIPPING COST IN CENTS:', shippingCostCents);
  
  // Fix rounding issues by ensuring consistent price calculations
  // Make sure we're using exact cents values for all calculations
  
  // Setup line items based on whether we have individual items or just a single item
  const lineItems = [
    // Create a single line item for the entire order
    {
      name: params.item_name,
      // Ensure consistent rounding - use the TOTAL price (already includes quantity * price for all items)
      price: Math.round(params.price * 100) / 100,
      quantity: 1, // Always use quantity 1 since total already includes all quantities
      description: params.items && params.items.length > 1 
        ? `Multiple parts (${params.items.length} items)` 
        : `3D part - ${params.file_name || 'Custom Part'}`
    }
  ];
    
  // Add shipping as a separate line item if cost provided
  if (shippingCostCents > 0) {
    console.log(`\n
✅ ADDING SHIPPING LINE ITEM: $${(shippingCostCents/100).toFixed(2)}
\n`);
    
    lineItems.push({
      name: 'Shipping & Handling',
      price: shippingCostCents / 100, // Convert back to dollars for the line item
      quantity: 1,
      description: 'Standard shipping'
    });
  } else {
    console.log(`\n
❌ NOT ADDING SHIPPING LINE ITEM - Value is $${(shippingCostCents/100).toFixed(2)}
\n`);
  }
  
  // Use the exact total amount from the cart - this already includes all items with quantities and shipping
  // We don't need to recalculate this as it should match exactly what's displayed in the UI
  const roundedTotalAmount = Math.round(params.price * 100) / 100;
  
  // Create a request that includes all items and shipping
  const requestBody = {
    // Base params for backward compatibility
    item_name: params.item_name,
    // Use the pre-calculated rounded total to ensure consistency 
    price: roundedTotalAmount,
    currency: params.currency || 'usd',
    quantity: 1, // Always use 1 as quantity because total price already includes all items and quantities
    quote_id: params.quote_id || '',
    file_name: params.file_name || '',
    shipping_cost: Number(params.shipping_cost || 0), // Ensure this is a number
    
    // Add the line items we constructed
    line_items: lineItems,
    
    // CRITICAL: Set up mode and special Stripe display flags for shipping
    mode: 'payment',
    shipping_options: [
      {
        shipping_rate_data: {
          display_name: 'Standard Shipping',
          type: 'fixed_amount',
          fixed_amount: {
            amount: shippingCostCents,
            currency: params.currency?.toLowerCase() || 'usd'
          }
        }
      }
    ],
    
    // Include metadata for tracking
    metadata: {
      quote_id: params.quote_id || '',
      file_name: params.file_name || '',
      shipping_cost: params.shipping_cost ? params.shipping_cost.toString() : '0',
      item_count: params.items ? params.items.length.toString() : '1',
      // Add all quote IDs and filenames in a compact format for webhook processing
      all_quote_ids: params.items ? params.items.map(item => item.id).join(',') : params.quote_id || '',
      all_file_names: params.items ? params.items.map(item => item.name).join(',') : params.file_name || '',
      // Add materials and quantities for webhook processing
      material: params.material || (params.items && params.items[0] ? params.items[0].material : ''),
      quantity: params.quantity || (params.items && params.items[0] ? params.items[0].quantity.toString() : '1'),
      all_materials: params.items ? params.items.map(item => item.material || '').join(',') : params.material || '',
      all_quantities: params.items ? params.items.map(item => item.quantity.toString()).join(',') : params.quantity || '1',
      // Add total price information using the rounded value
      total_items_price: roundedTotalAmount.toString()
    }
  };
  
  // Explicit terminal logging for the final total amount
  console.log('\n===== FINAL CHECKOUT TOTALS (TERMINAL) =====');
  console.log('ITEMS TOTAL:', params.items 
    ? params.items.reduce((sum, item) => sum + (item.price * item.quantity), 0).toFixed(2)
    : params.price.toFixed(2));
  console.log('SHIPPING COST:', (shippingCostCents/100).toFixed(2));
  console.log('CALCULATED TOTAL:', roundedTotalAmount.toFixed(2));
  console.log('LINE ITEMS COUNT:', requestBody.line_items.length);
  
  console.log(`\n
📦 CHECKOUT REQUEST DETAILS 📦
Total Items: ${requestBody.metadata.item_count}
Items Price: $${requestBody.metadata.total_items_price}
Shipping Cost: $${requestBody.metadata.shipping_cost}
Line Items Count: ${lineItems.length}
\n`);

  // Log the FULL request body with shipping emphasized
  console.log(`\n
🔍 FULL REQUEST BODY 🔍
${JSON.stringify({
  ...requestBody,
  shipping_cost_highlighted: requestBody.shipping_cost,
  total_calculated: roundedTotalAmount
}, null, 2)}
\n`);

  try {
    const response = await fetch(`${API_BASE_URL}/create-checkout-session`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(requestBody),
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
  material?: string;
  process?: string;
  technology?: string;
  description?: string;
}

export interface CreatePaymentIntentRequest {
  items: SimpleCartItem[];
  currency?: string;
  customer_email?: string;
  // Add other fields matching backend Pydantic model PaymentIntentRequest if needed
  metadata?: Record<string, string>;
  couponCode?: string;
}

export interface PaymentIntentResponse {
  clientSecret?: string;
  paymentIntentId?: string;
  amount?: number;
  currency?: string;
  error?: string;
  discount?: number;
  isTestMode?: boolean;
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