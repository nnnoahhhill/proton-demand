# ProtonDemand Deployment Guide

This guide will walk you through setting up and deploying your ProtonDemand application with a split deployment approach - frontend on Vercel and backend self-hosted on your PC.

## Overview

The application consists of two main components:
1. **Frontend**: Next.js application (deployed on Vercel)
2. **Backend**: Python-based quote system (self-hosted)

## Prerequisites

- A domain name you own
- A Stripe account
- A Slack workspace with appropriate permissions
- A computer that will serve as your backend server (available 24/7)
- Basic knowledge of networking and port forwarding

## 1. Backend Setup (Self-Hosted)

The backend needs to be hosted on a computer with reliable internet access, as it handles file processing and integrates with Stripe webhooks.

### 1.1 Environment Setup

1. Clone the repository on your backend server:
   ```bash
   git clone <your-repo-url>
   cd protondemand
   ```

2. Install backend dependencies:
   ```bash
   cd backend/quote_system
   pip install -r requirements.txt
   ```

3. Copy and configure the backend environment file:
   ```bash
   cp .env.example .env
   ```

4. Edit the `.env` file with appropriate settings:
   ```
   # Recommended production settings
   LOG_LEVEL=INFO
   API_HOST=0.0.0.0  # Listen on all interfaces
   API_PORT=8000     # Default port
   API_RELOAD=false  # Disable auto-reload for production
   MAX_UPLOAD_SIZE_MB=250
   ```

5. Storage directories (these have already been set up at these paths):
   ```bash
   # Your storage directories are already configured at:
   # /home/noah/Sidework/repos/protondemand/storage/models
   # /home/noah/Sidework/repos/protondemand/storage/fff-configs
   # /home/noah/Sidework/repos/protondemand/storage/orders
   # /home/noah/Sidework/repos/protondemand/logs
   
   # Make sure these directories have the right permissions
   chmod -R 755 /home/noah/Sidework/repos/protondemand/storage
   chmod -R 755 /home/noah/Sidework/repos/protondemand/logs
   ```

### 1.2 Network Configuration (Without Port Forwarding)

Instead of configuring port forwarding on your router, you can use secure tunneling services to expose your backend:

#### Option 1: Cloudflare Tunnel (Recommended)

1. Sign up for a Cloudflare account and add your domain:
   - Go to https://dash.cloudflare.com/sign-up
   - After creating an account, click "Add a Site"
   - Enter your root domain (protondemand.com)
   - Select the Free plan
   - Follow the instructions to update your domain's nameservers at your registrar
   - Wait for DNS propagation (usually takes 24-48 hours)
   
   For your setup, add your root domain (protondemand.com) to Cloudflare, then create the API subdomain later during tunnel configuration.

2. Install cloudflared:
   ```bash
   # On Ubuntu/Debian
   curl -L --output cloudflared.deb https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
   sudo dpkg -i cloudflared.deb
   
   # On macOS
   brew install cloudflared
   ```

3. Authenticate cloudflared:
   ```bash
   cloudflared tunnel login
   ```

4. Create a tunnel:
   ```bash
   cloudflared tunnel create protondemand
   ```

5. Configure your tunnel by creating a config file at `~/.cloudflared/config.yml`:
   ```yaml
   tunnel: <TUNNEL_ID>
   credentials-file: /home/<your-username>/.cloudflared/<TUNNEL_ID>.json
   
   ingress:
     - hostname: api.yourdomain.com
       service: http://localhost:8000
     - service: http_status:404
   ```

6. Create DNS record for your tunnel:
   ```bash
   cloudflared tunnel route dns <TUNNEL_ID> api.yourdomain.com
   ```

7. Run your tunnel as a service:
   ```bash
   # Make sure to specify the config file path
   sudo cloudflared --config ~/.cloudflared/config.yml service install
   sudo systemctl start cloudflared
   
   # Verify the service is running
   sudo systemctl status cloudflared
   ```
   
   Note: If you still encounter issues, you can run it manually to debug:
   ```bash
   # Run in foreground to check for errors
   cloudflared tunnel --config ~/.cloudflared/config.yml run
   ```

#### Option 2: ngrok

1. Sign up for an ngrok account and get your auth token.

2. Install ngrok:
   ```bash
   curl -s https://ngrok-agent.s3.amazonaws.com/ngrok.asc | sudo tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null
   echo "deb https://ngrok-agent.s3.amazonaws.com buster main" | sudo tee /etc/apt/sources.list.d/ngrok.list
   sudo apt update && sudo apt install ngrok
   ```

3. Authenticate ngrok:
   ```bash
   ngrok config add-authtoken <YOUR_AUTH_TOKEN>
   ```

4. Set up a custom domain (requires paid plan):
   - In ngrok dashboard, add your custom domain (api.yourdomain.com)
   - Add CNAME record in your domain DNS: `api.yourdomain.com` pointing to `<id>.ngrok-custom.com`

5. Create a systemd service for ngrok:
   ```bash
   sudo nano /etc/systemd/system/ngrok.service
   ```

6. Add the following configuration:
   ```
   [Unit]
   Description=ngrok
   After=network.target
   
   [Service]
   User=<your-username>
   ExecStart=ngrok http --domain=api.yourdomain.com 8000
   Restart=always
   RestartSec=5
   
   [Install]
   WantedBy=multi-user.target
   ```

7. Enable and start the service:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable ngrok
   sudo systemctl start ngrok
   ```

#### Option 3: Tailscale (Best for Teams)

1. Install Tailscale on both your server and development machines:
   ```bash
   curl -fsSL https://tailscale.com/install.sh | sh
   ```

2. Log in on your server:
   ```bash
   sudo tailscale up
   ```

3. Enable Tailscale Serve to expose your backend:
   ```bash
   sudo tailscale serve https:443 http://localhost:8000
   ```

4. Create a MagicDNS custom name or use Tailscale's Funnel feature:
   ```bash
   # For Funnel (public access)
   sudo tailscale serve --https=443 --set-path=/ http://localhost:8000
   tailscale funnel 443 on
   ```

5. Update your frontend environment to use the Tailscale hostname:
   ```
   NEXT_PUBLIC_API_BASE_URL=https://<your-tailscale-hostname>
   ```

Configure your frontend on Vercel to use the appropriate URL from whichever method you choose.

### 1.3 Running the Backend as a Service

1. Create a systemd service to keep the backend running:

   ```bash
   sudo nano /etc/systemd/system/protondemand.service
   ```

2. Add the following configuration for conda environment (with your specific paths and keys):

   ```
   [Unit]
   Description=ProtonDemand Backend Service
   After=network.target

   [Service]
   User=noah
   WorkingDirectory=/home/noah/Sidework/repos/protondemand/backend
   # Activate conda environment and run the API with your preferred command
   ExecStart=/bin/zsh -c 'source ~/.zshrc && conda activate quote-env && uvicorn quote_system.main_api:app --host 0.0.0.0 --port 8000'
   Restart=always
   RestartSec=5
   Environment=PYTHONUNBUFFERED=1
   # Essential environment variables
   Environment=LOG_LEVEL=INFO
   Environment=API_HOST=0.0.0.0
   Environment=API_PORT=8000
   Environment=API_RELOAD=false
   Environment=MAX_UPLOAD_SIZE_MB=250
   # Slicers
   Environment=PRUSA_SLICER_PATH=/usr/bin/prusa-slicer
   # Stripe API keys
   Environment=STRIPE_SECRET_KEY=sk_test_your_stripe_secret_key_here
   Environment=STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret_here
   # Slack integration
   Environment=SLACK_BOT_TOKEN=xoxb-your_slack_bot_token_here
   Environment=SLACK_UPLOAD_CHANNEL_ID=your_channel_id_here
   Environment=SLACK_WEBHOOK_URL=https://hooks.slack.com/services/your/webhook/url
   # File storage paths (your specific paths)
   Environment=STORAGE_PATH=/home/noah/Sidework/repos/protondemand/storage
   Environment=MODELS_PATH=/home/noah/Sidework/repos/protondemand/storage/models
   Environment=ORDERS_PATH=/home/noah/Sidework/repos/protondemand/storage/orders
   # Application settings
   Environment=FRONTEND_URL=https://protondemand.com
   Environment=NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_test_your_stripe_publishable_key_here

   [Install]
   WantedBy=multi-user.target
   ```
   
   Note: Adjust the conda path and environment variables based on your specific setup. If you installed conda at a different location, update the path accordingly.

3. Enable and start the service:

   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable protondemand
   sudo systemctl start protondemand
   ```

4. Check the service status:

   ```bash
   sudo systemctl status protondemand
   ```

### 1.4 Securing the Backend (Optional)

There are multiple ways to secure your backend with HTTPS. If you're using Cloudflare Tunnel or another tunneling service from section 1.2, you can **skip this section entirely** since they already provide HTTPS termination.

#### Option 1: Using Cloudflare Tunnel (Recommended)

If you've set up Cloudflare Tunnel as described in section 1.2, your backend is already secured with HTTPS and you don't need to configure Nginx. Cloudflare handles the TLS termination and routes traffic securely to your backend.

#### Option 2: Using Nginx as a reverse proxy

If you prefer to use Nginx for TLS termination (not required if using a tunnel):

1. Install Nginx and Certbot:

   ```bash
   # For Ubuntu/Debian
   sudo apt install nginx certbot python3-certbot-nginx
   
   # For Arch Linux
   sudo pacman -S nginx certbot certbot-nginx
   ```

2. Create an Nginx configuration:

   ```bash
   # For Ubuntu/Debian
   sudo nano /etc/nginx/sites-available/protondemand
   
   # For Arch Linux
   sudo nano /etc/nginx/conf.d/protondemand.conf
   ```

3. Add the following configuration:

   ```
   server {
       listen 80;
       server_name api.yourdomain.com;

       location / {
           proxy_pass http://localhost:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
           
           # Allow large file uploads
           client_max_body_size 250M;
       }
   }
   ```

   > **IMPORTANT NOTE**: Make sure your Nginx config is correctly formatted. Common issues include:
   > - Ensure Nginx is only listening on port 80 (and later 443), not on port 8000 which is used by the backend
   > - If you see errors like "bind() to 0.0.0.0:8000 failed (98: Address already in use)" during Nginx restart,
   >   it means your Nginx is trying to listen on the same port as your backend application
   > - Check your main nginx.conf file (/etc/nginx/nginx.conf) for any server blocks that might be listening on port 8000
   >   and change those to use a different port (e.g., 8001) or disable/comment them out

4. Enable the site and obtain an SSL certificate:

   ```bash
   # For Ubuntu/Debian
   sudo ln -s /etc/nginx/sites-available/protondemand /etc/nginx/sites-enabled/
   sudo certbot --nginx -d api.yourdomain.com
   
   # For Arch Linux
   # No need to create symlinks as configs in conf.d are automatically loaded
   sudo certbot --nginx -d api.yourdomain.com
   
   # For all systems
   sudo systemctl restart nginx
   ```

## 2. Frontend Setup (Vercel)

### 2.1 Prepare Environment Variables

1. Create a `.env` file in the project root with the following variables:

   ```
   # API Base URL - point to your backend
   NEXT_PUBLIC_API_BASE_URL=https://api.protondemand.com
   
   # Stripe API keys
   NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_test_your_stripe_publishable_key_here
   STRIPE_SECRET_KEY=sk_test_your_stripe_secret_key_here
   STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret_here
   
   # Slack API
   SLACK_BOT_TOKEN=xoxb-your_slack_bot_token_here
   SLACK_UPLOAD_CHANNEL_ID=your_channel_id_here
   SLACK_WEBHOOK_URL=https://hooks.slack.com/services/your/webhook/url
   
   # Application settings
   FRONTEND_URL=https://protondemand.com
   NEXT_PUBLIC_BASE_URL=https://protondemand.com
   
   # General Settings
   LOG_LEVEL=INFO
   
   # API Settings
   API_RELOAD=false
   
   # Slicer Configuration
   PRUSA_SLICER_PATH=/usr/bin/prusa-slicer
   ```

### 2.2 Deploy to Vercel

1. Sign up for a Vercel account if you don't have one.

2. Install the Vercel CLI:
   ```bash
   npm install -g vercel
   ```

3. Configure the Vercel project:
   ```bash
   vercel
   ```
   Follow the prompts to set up the project.

4. Add the environment variables to your Vercel project through the dashboard or using:
   ```bash
   vercel env add
   ```
   Add each of the environment variables from your .env file.

5. Deploy the project:
   ```bash
   vercel --prod
   ```

6. Configure your domain in the Vercel dashboard under Project Settings > Domains.

## 3. Stripe Configuration

### 3.1 Set Up Stripe Webhooks

1. Log in to your Stripe Dashboard.

2. Go to Developers > Webhooks > Add Endpoint.

3. Add the following endpoints:
   - For testing: `https://yourdomain.com/api/notify-order`
   - For production: `https://yourdomain.com/api/notify-order`

4. Select the following events:
   - `payment_intent.succeeded`
   - `checkout.session.completed`

5. Get the webhook signing secret and add it to your environment variables.

### 3.2 Create Admin Coupon for Testing in Production

1. In the Stripe Dashboard, go to Products > Coupons.

2. Create a new coupon with:
   - Code: A long, complex, hard-to-guess code (e.g., `ADMIN_TEST_9a7b3c2d1e5f`)
   - Discount: 100% off
   - Set an expiration date if desired

3. Add this coupon code to your frontend code at `/app/api/create-payment-intent/route.ts`:

   ```typescript
   const validTestCodes: Record<string, number> = {
     'ADMINTEST': 100,
     'TEST50OFF': 50,
     'PROTONDEV': 100,
     'ADMIN_TEST_9a7b3c2d1e5f': 100 // Your new complex code
   };
   ```

### 3.3 Switch from Test to Live Mode

1. In the Stripe Dashboard, toggle from "Test Mode" to "Live Mode".

2. Generate new live API keys.

3. Update your environment variables with the live keys.

4. Create a new webhook endpoint for the live environment.

## 4. Slack Configuration

1. Create a Slack app at https://api.slack.com/apps.

2. Add the following permissions:
   - `chat:write`
   - `files:write`
   - `incoming-webhook`

3. Install the app to your workspace.

4. Create a channel for order notifications.

5. Get the Bot Token, Webhook URL, and Channel ID and add them to your environment variables.

## 5. Final Configuration

### 5.1 Update Callback URLs

1. Update the Stripe webhook callback URL in your Stripe Dashboard to point to your production domain.

2. Update the Slack app's redirect URLs if you're using Slack OAuth.

### 5.2 Test the Deployment

1. Try placing a test order using your admin coupon code.

2. Verify that Slack notifications are working correctly.

3. Check that model files are being properly saved and processed.

## 6. Maintenance and Monitoring

### 6.1 Backend Server Monitoring

1. Set up basic monitoring for your backend server:
   ```bash
   sudo apt install htop
   ```

2. Check the logs regularly:
   ```bash
   sudo journalctl -u protondemand -f
   ```

3. Monitor the application logs:
   ```bash
   tail -f /path/to/protondemand/logs/latest.log
   ```

### 6.2 Backup Strategy

1. Set up regular backups of your model and order files:
   ```bash
   # Example backup script
   rsync -av /path/to/protondemand/storage/ /path/to/backup/
   ```

2. Create a cron job to run this backup regularly:
   ```bash
   crontab -e
   # Add: 0 2 * * * /path/to/backup_script.sh
   ```

## Troubleshooting

### Common Issues

1. **Webhook Failures**: Check that your webhook URLs are correct and accessible from the internet.

2. **File Upload Issues**: Verify that your server has enough disk space and that file permissions are correct.

3. **Missing Slack Notifications**: Ensure your Slack tokens are correct and that the bot has appropriate permissions.

4. **Backend Connection Issues**: Check that your port forwarding is correctly configured.

### Logs and Debugging

- Frontend logs will be available in the Vercel dashboard.
- Backend logs will be stored in `/path/to/protondemand/logs/`.
- Stripe webhook events can be monitored in the Stripe Dashboard.

## Security Considerations

1. **Stripe API Keys**: Never expose your Stripe secret keys to the client-side code.

2. **File Access**: Restrict access to your model and order files with proper permissions.

3. **SSL/TLS**: Always use HTTPS for production environments.

4. **Regular Updates**: Keep all dependencies updated to patch security vulnerabilities.

## Conclusion

Your ProtonDemand application should now be fully deployed with the frontend on Vercel and the backend self-hosted on your PC. This setup allows you to manage large files and complex processing tasks on your own hardware while leveraging Vercel's global CDN for the frontend.

If you encounter any issues during deployment, refer to the project documentation or reach out to the development team for assistance.