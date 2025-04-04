# Stripe and Slack Integration Guide

This document provides detailed information on how to set up and use the Stripe payment processing and Slack notification features in the ProtonDemand application.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Setting Up Stripe](#setting-up-stripe)
3. [Setting Up Slack](#setting-up-slack)
4. [Environment Configuration](#environment-configuration)
5. [Testing the Integration](#testing-the-integration)
6. [Troubleshooting](#troubleshooting)

## Prerequisites

Before setting up the integration, ensure you have:

- A Stripe account (you can create one at [stripe.com](https://stripe.com))
- A Slack workspace with permission to create apps and webhooks
- The required packages installed in your environment (see [Setup Guide](../setup_guide.md))

## Setting Up Stripe

### 1. Create a Stripe Account

If you don't already have one, sign up for a Stripe account at [stripe.com](https://stripe.com).

### 2. Get API Keys

1. Log in to your Stripe Dashboard
2. Go to Developers > API keys
3. Note down your Publishable key and Secret key
4. For testing, use the test mode keys

### 3. Set Up Webhook (Optional)

For production use, you should set up a webhook to receive payment events:

1. Go to Developers > Webhooks
2. Click "Add endpoint"
3. Enter your webhook URL (e.g., `https://yourdomain.com/api/stripe-webhook`)
4. Select the events you want to receive (at minimum: `payment_intent.succeeded`, `payment_intent.payment_failed`)
5. Note down the Webhook Signing Secret

## Setting Up Slack

### 1. Create a Slack App

1. Go to [api.slack.com/apps](https://api.slack.com/apps)
2. Click "Create New App"
3. Choose "From scratch"
4. Name your app (e.g., "ProtonDemand Orders") and select your workspace
5. Click "Create App"

### 2. Configure Bot Permissions

1. In your app settings, go to "OAuth & Permissions"
2. Under "Scopes", add the following Bot Token Scopes:
   - `chat:write`
   - `files:write`
   - `channels:read`
3. Click "Install to Workspace" and authorize the app

### 3. Create a Webhook

1. Go to "Incoming Webhooks"
2. Toggle "Activate Incoming Webhooks" to On
3. Click "Add New Webhook to Workspace"
4. Select the channel where you want to receive order notifications
5. Click "Allow"
6. Copy the Webhook URL

### 4. Get Channel ID

1. In Slack, right-click on the channel you selected
2. Select "Copy Link"
3. The channel ID is the alphanumeric code after the last slash (e.g., `C0123456789`)

## Environment Configuration

Create a `.env` file in the project root with the following variables:

```
# Stripe API keys
STRIPE_PUBLIC_KEY=pk_test_your_public_key
STRIPE_SECRET_KEY=sk_test_your_secret_key
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret

# Slack API
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/your/webhook/url
SLACK_CHANNEL_ID=C0123456789

# Make the public key available to the frontend
NEXT_PUBLIC_STRIPE_PUBLIC_KEY=pk_test_your_public_key
```

## Testing the Integration

### Testing Stripe Integration

1. Run the application in development mode
2. Go to the checkout page
3. Use Stripe's test card numbers:
   - Success: `4242 4242 4242 4242`
   - Decline: `4000 0000 0000 0002`
4. Use any future expiration date, any 3-digit CVC, and any postal code

### Testing Slack Integration

1. Place a test order using the Stripe test card
2. Check your Slack channel for the order notification
3. Verify that all order details and files are included

## Troubleshooting

### Stripe Issues

- **Payment fails**: Check the Stripe Dashboard > Events to see the error details
- **API key errors**: Ensure your API keys are correctly set in the `.env` file
- **Webhook errors**: Check that your webhook URL is accessible and the signing secret is correct

### Slack Issues

- **No notifications**: Check that your bot token and webhook URL are correct
- **Missing permissions**: Ensure your Slack app has the required scopes
- **File upload fails**: Verify that your bot has the `files:write` permission

### General Issues

- **Environment variables**: Run the test script to verify all environment variables are set
- **Package installation**: Ensure all required packages are installed in your environment
- **API errors**: Check the server logs for detailed error messages
