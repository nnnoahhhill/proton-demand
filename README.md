# ProtonDemand Manufacturing Platform

A full-stack platform for on-demand manufacturing services including 3D printing, CNC machining, and sheet metal fabrication.

## Features

- Instant quotes for 3D manufacturing processes
- Real-time model visualization
- Secure payment processing with Stripe
- Automated order notification system
- Smart DFM (Design for Manufacturing) analysis
- File storage for 3D models and engineering drawings

## Environment Variables

To run this project, you will need to add the following environment variables to your `.env` file (create one if it doesn't exist):

```
# Frontend (Next.js - prefix with NEXT_PUBLIC_)
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_test_YOUR_PUBLISHABLE_KEY
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000

# Backend (FastAPI)
STRIPE_SECRET_KEY=sk_test_YOUR_SECRET_KEY
STRIPE_WEBHOOK_SECRET=whsec_YOUR_WEBHOOK_SECRET
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
SLACK_BOT_TOKEN=xoxb-YOUR-SLACK-BOT-TOKEN
SLACK_CHANNEL_ID=YOUR-SLACK-CHANNEL-ID

# Optional - for file storage configuration
STORAGE_BASE_DIR=/path/to/persistent/storage
```

**Note:** Replace the placeholder values with your actual keys and URLs.

## File Storage System

The platform includes a file storage system for 3D models that:

- Stores files with quote ID reference for easy tracking
- Uses a structured naming convention: `{quoteID}_{filename}`
- Supports STL, STEP, STP, and OBJ file formats
- Saves files to a configurable persistent storage location

### Storage Workflow

1. When a quote is generated, the 3D model file is temporarily stored in localStorage
2. During checkout, file metadata is passed to the server
3. Upon successful order placement, the file is:
   - Saved to the server's filesystem with the quote ID as a prefix
   - Attached to the Slack notification
   - Associated with the order for future reference

## Slack Notification System

Orders generate detailed Slack notifications that include:

- Customer information (name, contact details, shipping address)
- Order date in PST/PDT timezone
- Quote ID reference number
- Order details (technology, material, quantity)
- Direct attachment of the 3D model file
- No pricing or payment information (per requirements)

### Notification Format

The Slack message uses a structured format with clearly defined sections:

```
🧱 New Manufacturing Order: ORD-123456

Customer: John Smith
Email: john@example.com

Order Date (PST): April 17, 2025, 10:00 AM

Quote ID: Q-12345678
Order ID: ORD-123456

Items:
• 5x example.stl (3D Printing, FDM, PLA, Standard High-Quality)

Shipping Address:
123 Main St
San Francisco, CA 94105
United States

[File Attachment: example_QuoteID-Q-12345678.stl]
```

## Testing

To test the platform locally:

1. Start the backend API server
2. Run the Next.js frontend
3. Generate a quote for a 3D model
4. Complete the checkout process
5. Verify the Slack notification and file storage

For testing Stripe payments, use test card numbers:
- Success: 4242 4242 4242 4242
- Decline: 4000 0000 0000 0002

## Maintenance

### File Storage

The file storage system is designed to be minimal and direct. For production:

- Consider implementing a cloud storage solution (AWS S3, Google Cloud Storage)
- Set up regular backups of the storage directory
- Implement file cleanup for abandoned quotes

### Slack Integration

The Slack integration can be configured with different webhook URLs for:
- Development environment (test notifications)
- Production environment (real order notifications)

Configure these in your environment variables as needed.