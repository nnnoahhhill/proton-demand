declare module 'occt-import-js' {
    // Add basic types based on usage, can be expanded if needed
    export interface ImportSettings {
        // Define specific parameters if known, or use a general type
        ReadStepFileParameters?: {
            ReadShapeCompoundMode?: boolean;
            // Add other STEP parameters if needed
        };
        // Add parameters for other formats if used (e.g., IGES)
    }

    export interface ImportResult {
        model: ArrayBuffer | null; // The resulting GLTF model as ArrayBuffer
        error: string | null;
        logs: string[];
    }

    export type ImportCallback = (result: ImportResult) => void;
    export type ErrorCallback = (error: any) => void; // Error can be of various types
    export type ProgressCallback = (progress: number) => void; // Progress from 0 to 1

    export class OCCTWorkerManager {
        constructor(wasmUrl: string); // URL to the .wasm file

        ImportModel(
            fileName: string, // Original name of the input file (e.g., 'model.step')
            fileBuffer: ArrayBuffer, // Content of the input file
            settings: ImportSettings, // Import settings object
            callbacks: {
                onSuccess: ImportCallback;
                onError: ErrorCallback;
                onProgress?: ProgressCallback; // Optional progress callback
            }
        ): void;

        // Add other methods if you use them (e.g., for cancelling, getting worker status)
    }

    // Add default export as a fallback if the library might export this way
    // Check the library's documentation or source for the correct export pattern
    const DefaultExport: typeof OCCTWorkerManager;
    export default DefaultExport;
} 