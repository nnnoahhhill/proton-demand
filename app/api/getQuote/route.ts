import { NextRequest, NextResponse } from 'next/server';
import { exec } from 'child_process';
import { promises as fs } from 'fs';
import { join } from 'path';
import * as path from 'path';
import { v4 as uuidv4 } from 'uuid';
import { mkdir, writeFile } from 'fs/promises';

// Validate process type
const validProcesses = ['CNC', '3DP_SLA', '3DP_SLS', '3DP_FDM', 'SHEET_METAL'];

// Validate materials based on process
const validMaterials: Record<string, string[]> = {
  'CNC': [
    'ALUMINUM_6061', 'MILD_STEEL', 'STAINLESS_STEEL_304', 'STAINLESS_STEEL_316', 
    'TITANIUM', 'COPPER', 'BRASS', 'HDPE', 'POM_ACETAL', 'ABS', 
    'ACRYLIC', 'NYLON', 'PEEK', 'PC'
  ],
  '3DP_SLA': ['STANDARD_RESIN'],
  '3DP_SLS': ['NYLON_12_WHITE', 'NYLON_12_BLACK'],
  '3DP_FDM': ['PLA', 'ABS', 'NYLON_12', 'ASA', 'PETG', 'TPU'],
  'SHEET_METAL': [
    'ALUMINUM_6061', 'MILD_STEEL', 'STAINLESS_STEEL_304', 'STAINLESS_STEEL_316', 
    'TITANIUM', 'COPPER', 'BRASS'
  ]
};

// Validate finishes based on process
const validFinishes: Record<string, string[]> = {
  'CNC': ['STANDARD', 'FINE', 'MIRROR'],
  '3DP_SLA': ['STANDARD', 'FINE'],
  '3DP_SLS': ['STANDARD'],
  '3DP_FDM': ['STANDARD', 'FINE'],
  'SHEET_METAL': ['STANDARD', 'PAINTED', 'ANODIZED', 'POWDER_COATED']
};

// Define response type
interface QuoteResponse {
  success: boolean;
  quoteId?: string;
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
    volume: number; // in cubic mm
    surfaceArea: number; // in square mm
  };
  dfmIssues?: Array<{
    type: string;
    severity: string;
    description: string;
    location?: {
      x: number;
      y: number;
      z: number;
    };
  }>;
  message?: string;
  error?: string;
}

// Helper function to run the Python DFM analysis script
const runDfmAnalysis = async (
  filePath: string,
  processType: string,
  material: string,
  finish: string
): Promise<any> => {
  return new Promise((resolve, reject) => {
    // Convert process to Python enum format
    let pythonProcess = '';
    if (processType === 'CNC') {
      pythonProcess = 'cnc_machining';
    } else if (processType.startsWith('3DP_')) {
      pythonProcess = '3d_printing';
    } else if (processType === 'SHEET_METAL') {
      pythonProcess = 'sheet_metal';
    }

    // For 3D printing, we need to specify the technology
    let printingTech = '';
    if (processType === '3DP_SLA') {
      printingTech = '--printing_technology sla';
    } else if (processType === '3DP_SLS') {
      printingTech = '--printing_technology sls';
    } else if (processType === '3DP_FDM') {
      printingTech = '--printing_technology fdm';
    }

    // Run the Python script with proper cwd
    const projectRoot = process.cwd();
    const command = `cd "${projectRoot}" && python dfm/manufacturing_dfm_api.py analyze --file "${filePath}" --method ${pythonProcess} --material ${material} --finish ${finish.toLowerCase()} ${printingTech} --detailed true`;

    exec(command, (error, stdout, stderr) => {
      if (error) {
        reject({
          error: true,
          message: `DFM analysis failed: ${error.message}`,
          stderr
        });
        return;
      }

      try {
        const result = JSON.parse(stdout);
        resolve(result);
      } catch (e) {
        reject({
          error: true,
          message: 'Failed to parse DFM analysis result',
          stdout,
          stderr
        });
      }
    });
  });
};

// Helper function to validate file type
const validateFileType = (filename: string): boolean => {
  const ext = path.extname(filename).toLowerCase();
  return ext === '.stl' || ext === '.step' || ext === '.stp';
};

// Main API handler
export async function POST(request: NextRequest): Promise<NextResponse> {
  try {
    // Generate a unique ID for this quote
    const quoteId = uuidv4();
    
    // Create temp directory for file storage if it doesn't exist
    const projectRoot = process.cwd();
    const tmpDir = join(projectRoot, 'tmp', quoteId);
    await mkdir(tmpDir, { recursive: true });

    // Parse the form data
    const formData = await request.formData();
    
    // Extract and validate the process
    const processType = formData.get('process') as string;
    if (!processType || !validProcesses.includes(processType)) {
      return NextResponse.json(
        { 
          success: false, 
          error: `Invalid process type. Must be one of: ${validProcesses.join(', ')}` 
        }, 
        { status: 400 }
      );
    }
    
    // Extract and validate the material
    const material = formData.get('material') as string;
    if (!material || !validMaterials[processType].includes(material)) {
      return NextResponse.json(
        { 
          success: false, 
          error: `Invalid material for ${processType}. Must be one of: ${validMaterials[processType].join(', ')}` 
        }, 
        { status: 400 }
      );
    }
    
    // Extract and validate the finish
    const finish = formData.get('finish') as string;
    if (!finish || !validFinishes[processType].includes(finish)) {
      return NextResponse.json(
        { 
          success: false, 
          error: `Invalid finish for ${processType}. Must be one of: ${validFinishes[processType].join(', ')}` 
        }, 
        { status: 400 }
      );
    }
    
    // Get the 3D file
    const modelFile = formData.get('modelFile') as File;
    if (!modelFile) {
      return NextResponse.json(
        { 
          success: false, 
          error: 'No model file provided. Please upload a .stl or .step file.' 
        }, 
        { status: 400 }
      );
    }
    
    // Validate file type
    if (!validateFileType(modelFile.name)) {
      return NextResponse.json(
        { 
          success: false, 
          error: 'Invalid file type. Please upload a .stl or .step file.' 
        }, 
        { status: 400 }
      );
    }
    
    // Save the model file
    const modelFilePath = join(tmpDir, modelFile.name);
    const modelBuffer = Buffer.from(await modelFile.arrayBuffer());
    await writeFile(modelFilePath, modelBuffer);
    
    // Handle optional PDF drawing file if provided
    const drawingFile = formData.get('drawingFile') as File;
    let drawingFilePath = '';
    
    if (drawingFile) {
      const ext = path.extname(drawingFile.name).toLowerCase();
      if (ext !== '.pdf') {
        return NextResponse.json(
          { 
            success: false, 
            error: 'Invalid drawing file type. Please upload a .pdf file.' 
          }, 
          { status: 400 }
        );
      }
      
      drawingFilePath = join(tmpDir, drawingFile.name);
      const drawingBuffer = Buffer.from(await drawingFile.arrayBuffer());
      await writeFile(drawingFilePath, drawingBuffer);
    }
    
    // Run DFM analysis
    const dfmResult = await runDfmAnalysis(modelFilePath, processType, material, finish);
    
    // Check if the part is manufacturable
    if (!dfmResult.is_manufacturable) {
      return NextResponse.json({
        success: false,
        quoteId,
        message: 'Part cannot be manufactured due to DFM issues',
        dfmIssues: dfmResult.issues.map((issue: any) => ({
          type: issue.type,
          severity: issue.severity,
          description: issue.description,
          location: issue.location
        }))
      }, { status: 400 });
    }
    
    // Calculate final quote
    const response: QuoteResponse = {
      success: true,
      quoteId,
      price: dfmResult.costs?.total || dfmResult.basic_price,
      currency: 'USD',
      leadTimeInDays: dfmResult.lead_time_days,
      manufacturingDetails: {
        process: processType,
        material,
        finish,
        boundingBox: {
          x: dfmResult.bounding_box.x,
          y: dfmResult.bounding_box.y,
          z: dfmResult.bounding_box.z,
        },
        volume: dfmResult.manufacturing?.volume || 0,
        surfaceArea: dfmResult.manufacturing?.surface_area || 0,
      }
    };
    
    return NextResponse.json(response);
  } catch (error) {
    console.error('Error processing quote request:', error);
    
    return NextResponse.json({
      success: false,
      error: 'Failed to process quote request',
      message: error instanceof Error ? error.message : 'Unknown error occurred'
    }, { status: 500 });
  }
} 