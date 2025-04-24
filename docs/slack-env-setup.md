# Slack Integration Setup Guide

This document explains how to set up the Slack integration for contact forms and order notifications.

## Required Environment Variables

For the Slack integration to work properly, you need to add the following variables to your `.env.local` file at the root of the project:

```
# Slack API
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/your/webhook/url
SLACK_CHANNEL_ID=C0123456789
```

## Getting a Slack Webhook URL

1. Go to your Slack workspace and create a new app at https://api.slack.com/apps
2. Click "Create New App" and select "From scratch"
3. Give it a name like "ProtonDemand Notifications" and select your workspace
4. Click on "Incoming Webhooks" and activate it
5. Click "Add New Webhook to Workspace" and select the channel where you want to receive notifications
6. Copy the Webhook URL that's provided - it should look like: `https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX`
7. Uncomment and update the `SLACK_WEBHOOK_URL` value in your `.env.local` file

IMPORTANT: The webhook URL must start with `https://hooks.slack.com/services/` to be valid!

## Getting a Slack Bot Token (for file attachments)

If you want to send file attachments with your notifications:

1. In your Slack app settings, go to "OAuth & Permissions"
2. Add the following scopes:
   - `chat:write`
   - `files:write`
   - `incoming-webhook`
3. Click "Install App to Workspace"
4. Copy the "Bot User OAuth Token" that starts with "xoxb-"
5. Paste this token as the value for `SLACK_BOT_TOKEN` in your `.env.local` file

## Getting a Channel ID

To find your channel ID:

1. Open Slack in a web browser
2. Navigate to the channel where you want to send notifications
3. The URL will look like `https://app.slack.com/client/T12345678/C0123456789`
4. The part after the last slash is your channel ID (C0123456789)
5. Add this as `SLACK_CHANNEL_ID` in your `.env.local` file

## Testing the Integration

After setting up your environment variables:

1. Restart your development server
2. Submit a test contact form
3. You should see a notification in your Slack channel

If you're not seeing notifications, check your server logs for any error messages.