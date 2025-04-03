# Vercel Deployment Troubleshooting

If you're seeing the "Unexpected token '<', "<!DOCTYPE "... is not valid JSON" error, follow these steps to diagnose and fix the issue:

## First, Check the Network Tab

1. Open your browser's developer tools (F12)
2. Go to the Network tab
3. Submit a quote request
4. Look for the `/api/getQuote` request
5. Check the status code and response body

### Common Issues:

#### 1. 500 Internal Server Error
This means the Python function is crashing. In the Vercel dashboard:
- Go to Functions → Check the logs for the specific function
- Look for Python errors or tracebacks

#### 2. 404 Not Found
The endpoint is not being properly routed:
- Make sure your `vercel.json` is properly set up
- Check that the file paths in your build configuration are correct

#### 3. Timeout
If the function is taking too long:
- Try using the mock data setting in `getQuote.py`
- Consider optimizing the DFM analysis

## "Unexpected token" Error

This specific error means:
1. The server is returning HTML (not JSON)
2. JavaScript is trying to parse this HTML as JSON
3. The first character (`<`) in the HTML is not valid in JSON

### Quick Fixes:

1. **Try Adding a Simple Debug Mode**:
   - Update your Python handler to return simple mock data:
   ```python
   # At the top of your handler
   if self.path == "/api/getQuote" and "debug=true" in self.headers.get('Cookie', ''):
       self.send_response(200)
       self.send_header('Content-type', 'application/json')
       self.end_headers()
       self.wfile.write(json.dumps({"success": True, "message": "Debug mode"}).encode())
       return
   ```

2. **Check CORS Headers**:
   - Make sure your Vercel functions are configured to handle CORS correctly
   - The function should handle OPTIONS requests properly

3. **Test with a Minimal Example**:
   - Create a simplified Python function that just returns basic JSON
   - Test if this works without any DFM code

## Verifying Your Setup

1. **Local Testing**:
   ```bash
   npx vercel dev
   ```
   This runs the Vercel development environment locally

2. **Deploy Preview**:
   ```bash
   npx vercel
   ```
   This creates a preview deployment you can test

3. **Check All Routes**:
   Verify that all your routes are properly configured in the Vercel dashboard

## Specific Recommendations

Based on your current setup, here are specific things to check:

1. In `api/getQuote.py`:
   - The `do_POST` method should always return valid JSON
   - Add lots of debugging print statements that will show up in Vercel logs

2. In your frontend code:
   - Add error handling for the fetch calls
   - Check the raw response before trying to parse as JSON:
   ```javascript
   .then(response => {
     if (!response.ok) {
       return response.text().then(text => {
         console.error('Server response:', text);
         throw new Error(`API error: ${response.status}`);
       });
     }
     return response.json();
   })
   ```

3. In `vercel.json`:
   - Make sure the routes are properly configured
   - Check that the build configuration is correct

## Last Resort

If nothing else works:

1. Create a backup of your current project
2. Start with a minimal working example
3. Gradually add back your functionality until you find what's breaking

Remember that Vercel logs are your best friend when debugging serverless functions! 