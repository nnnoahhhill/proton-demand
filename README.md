## Environment Variables

To run this project, you will need to add the following environment variables to your `.env` file (create one if it doesn't exist):

\`\`\`
# Frontend (Next.js - prefix with NEXT_PUBLIC_)
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_test_YOUR_PUBLISHABLE_KEY

# Backend (FastAPI)
STRIPE_SECRET_KEY=sk_test_YOUR_SECRET_KEY
STRIPE_WEBHOOK_SECRET=whsec_YOUR_WEBHOOK_SECRET
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
\`\`\`

**Note:** Replace the placeholder values with your actual keys and URLs.

## Testing 