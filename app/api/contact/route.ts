import { NextRequest, NextResponse } from 'next/server';

// We'll build a simpler solution with direct fetch to avoid library issues
// and make it robust against missing environment variables

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    
    // Validate required fields
    const { name, email, subject, message } = body;
    if (!name || !email || !subject || !message) {
      return NextResponse.json(
        { error: 'All fields are required' },
        { status: 400 }
      );
    }
    
    // Format the message for Slack
    const blocks = [
      {
        type: 'header',
        text: {
          type: 'plain_text',
          text: `📧 New Contact Form Message`,
          emoji: true,
        },
      },
      {
        type: 'section',
        fields: [
          {
            type: 'mrkdwn',
            text: `*From:*\n${name}`,
          },
          {
            type: 'mrkdwn',
            text: `*Email:*\n${email}`,
          },
        ],
      },
      {
        type: 'section',
        text: {
          type: 'mrkdwn',
          text: `*Subject:*\n${subject}`,
        },
      },
      {
        type: 'section',
        text: {
          type: 'mrkdwn',
          text: `*Message:*\n${message}`,
        },
      },
      {
        type: 'divider'
      },
      {
        type: 'context',
        elements: [
          {
            type: 'mrkdwn',
            text: `Message received at ${new Date().toLocaleString()}`,
          },
        ],
      },
    ];
    
    // Always log the submission to console first (failsafe backup)
    console.log('CONTACT FORM SUBMISSION:', {
      name, email, subject, message, 
      date: new Date().toISOString()
    });
    
    // Check if we have a Slack webhook URL
    // Get the path from environment variable - it should be the one from your .env.local
    const webhookUrl = process.env.SLACK_WEBHOOK_URL;
    
    // Only attempt to send to Slack if we have a valid webhook URL
    // This prevents errors when the URL is not configured
    if (webhookUrl && webhookUrl.startsWith('https://hooks.slack.com/services/')) {
      try {
        // Format message for Slack
        const slackPayload = {
          text: `Contact Form: ${subject}`,
          blocks
        };
        
        // Use native fetch for maximum reliability
        const response = await fetch(webhookUrl, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(slackPayload)
        });
        
        if (!response.ok) {
          throw new Error(`Slack webhook returned ${response.status}: ${await response.text()}`);
        }
        
        console.log('Successfully sent to Slack');
      } catch (slackError) {
        // Log errors but don't fail the submission
        console.error('Failed to send to Slack:', slackError instanceof Error ? slackError.message : slackError);
      }
    } else {
      console.log('No valid Slack webhook URL configured. To enable Slack notifications, add SLACK_WEBHOOK_URL to your .env.local file.');
    }
    
    return NextResponse.json({
      success: true,
      message: 'Contact message received'
    });
  } catch (error) {
    console.error('Error processing contact form:', error);
    
    return NextResponse.json(
      { 
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error occurred' 
      },
      { status: 500 }
    );
  }
}