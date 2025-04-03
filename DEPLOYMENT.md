# Deploying to Vercel

This document outlines how to deploy both the Next.js frontend and Python backend to Vercel.

## Architecture Overview

The project uses:
- Next.js frontend
- Python serverless function for DFM analysis
- Integration between the two via API routes

## Deployment Steps

1. **Push your code to a Git repository**
   - GitHub, GitLab, or Bitbucket

2. **Connect to Vercel**
   - Go to [Vercel](https://vercel.com)
   - Create a new project
   - Connect to your Git repository

3. **Configure the project**
   - Framework Preset: Next.js
   - Environment Variables:
     - None required for basic setup

4. **Deploy**
   - Click Deploy button
   - Vercel will automatically detect both the Next.js frontend and Python serverless functions

## What Happens During Deployment

Vercel will:
1. Build the Next.js frontend using `@vercel/next`
2. Set up the Python serverless function using `@vercel/python`
3. Route requests appropriately based on the configuration in `vercel.json`

## File Structure for Deployment

- `/api/getQuote.py` - Python serverless function for quote generation
- `/api/requirements.txt` - Python dependencies for the serverless function
- `/api/vercel.json` - Configuration for including the dfm module
- `/vercel.json` - Main configuration for routing and builds

## Troubleshooting

If you encounter errors:

1. **Large file uploads failing**
   - Check that the form submission is properly formatted as multipart/form-data
   - Consider using Vercel's blob storage for large files

2. **"Unexpected token '<', '<!DOCTYPE'" errors**
   - This indicates an HTML error page is being returned instead of JSON
   - Check the server logs in Vercel dashboard
   - Ensure the Python handler is correctly returning JSON

3. **Timeout issues**
   - The current configuration allows 60 seconds for function execution
   - Consider optimizing the DFM analysis or using a more efficient approach
   - Look into Vercel's Edge Functions for longer-running operations

## Limitations

- **File Size**: Vercel has a limit on request/response size (typically around 4-5MB)
- **Execution Time**: Vercel serverless functions have time limits (30s on hobby plans, 60s on pro plans)
- **Memory**: The function is configured with 1GB of memory, which is the maximum allowed

## Testing the Deployment

After deployment, you can test the API with:

```javascript
async function testQuote() {
  const formData = new FormData();
  formData.append('model_file', /* your 3D model file */);
  formData.append('process', 'CNC');
  formData.append('material', 'aluminum_6061');
  formData.append('finish', 'standard');
  
  const response = await fetch('https://your-vercel-domain.vercel.app/api/getQuote', {
    method: 'POST',
    body: formData
  });
  
  const data = await response.json();
  console.log(data);
}
``` 