import { NextRequest, NextResponse } from 'next/server';
import { WebClient } from '@slack/web-api';
import { IncomingWebhook } from '@slack/webhook';
import { ContactSubmission } from '@/lib/slack';

// Initialize Slack clients
const slackClient = new WebClient(process.env.SLACK_BOT_TOKEN);
const webhook = new IncomingWebhook(process.env.SLACK_WEBHOOK_URL || '');
const channelId = process.env.SLACK_CHANNEL_ID || '';

export async function POST(req: NextRequest) {
  try {
    // Parse the multipart form data
    const formData = await req.formData();
    
    // Get the contact data
    const contactJson = formData.get('contact');
    if (!contactJson || typeof contactJson !== 'string') {
      return NextResponse.json(
        { error: 'Contact data is required' },
        { status: 400 }
      );
    }
    
    const contact: ContactSubmission = JSON.parse(contactJson);
    
    // Format the message for Slack
    const message = formatContactMessage(contact);
    
    // Send the message to Slack
    await webhook.send({
      text: `Contact Form: ${contact.subject}`,
      blocks: message,
    });
    
    // Upload files if provided
    const filePromises = [];
    for (let i = 0; formData.has(`file${i}`); i++) {
      const file = formData.get(`file${i}`) as File;
      if (file) {
        const buffer = Buffer.from(await file.arrayBuffer());
        
        filePromises.push(
          slackClient.files.upload({
            channels: channelId,
            filename: file.name,
            file: buffer,
            initial_comment: `File from contact form submission: ${contact.subject}`,
          })
        );
      }
    }
    
    // Wait for all file uploads to complete
    if (filePromises.length > 0) {
      await Promise.all(filePromises);
    }
    
    return NextResponse.json({
      success: true,
      message: 'Contact notification sent to Slack',
    });
  } catch (error) {
    console.error('Error sending contact notification to Slack:', error);
    
    return NextResponse.json(
      { 
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error occurred' 
      },
      { status: 500 }
    );
  }
}

/**
 * Format the contact message for Slack
 * 
 * @param contact Contact submission data
 * @returns Slack message blocks
 */
function formatContactMessage(contact: ContactSubmission) {
  return [
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
          text: `*From:*\n${contact.name}`,
        },
        {
          type: 'mrkdwn',
          text: `*Email:*\n${contact.email}`,
        },
      ],
    },
    {
      type: 'section',
      text: {
        type: 'mrkdwn',
        text: `*Subject:*\n${contact.subject}`,
      },
    },
    {
      type: 'section',
      text: {
        type: 'mrkdwn',
        text: `*Message:*\n${contact.message}`,
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
}