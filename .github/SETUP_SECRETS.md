# GitHub Actions Setup Instructions

## Required Secrets

You need to add these secrets to your GitHub repository:

### 1. Navigate to Repository Settings
- Go to your GitHub repository
- Click **Settings** → **Secrets and variables** → **Actions**
- Click **New repository secret**

### 2. Add GOOGLE_CLIENT_SECRET

**Name:** `GOOGLE_CLIENT_SECRET`

**Value:** Copy the entire contents of your `client_secret_544079871095-7eo15ghsvks1u43urcft84afblheu732.apps.googleusercontent.com.json` file

```bash
# Get the content (run this in your terminal):
cat /home/ivan/Documents/e-mail_processor/client_secret_544079871095-7eo15ghsvks1u43urcft84afblheu732.apps.googleusercontent.com.json
```

### 3. Add GOOGLE_TOKEN_JSON

**Name:** `GOOGLE_TOKEN_JSON`

**Value:** Copy the entire contents of your `token.json` file (after you've authenticated at least once locally)

```bash
# Get the content (run this in your terminal):
cat /home/ivan/Documents/e-mail_processor/token.json
```

**Important:** The `token.json` file is created after you run the script locally for the first time and complete the OAuth flow.

## Token Refresh Notes

- Google tokens expire after 7 days of inactivity (refresh tokens last longer)
- If your workflow runs regularly, the token should auto-refresh
- If it stops working, you may need to:
  1. Run the script locally again to get a new token
  2. Update the `GOOGLE_TOKEN_JSON` secret with the new token

## Schedule Customization

Edit `.github/workflows/process-invoices.yml` to change the schedule:

```yaml
schedule:
  # Daily at 9 AM UTC
  - cron: '0 9 * * *'
  
  # Every 6 hours
  - cron: '0 */6 * * *'
  
  # Monday-Friday at 8 AM UTC
  - cron: '0 8 * * 1-5'
```

## Manual Trigger

You can manually run the workflow:
1. Go to **Actions** tab
2. Click **Process Invoices**
3. Click **Run workflow**

## Security Note

- Never commit `token.json` or client secret files to git
- The `.gitignore` should already exclude these files
- Only store them as GitHub secrets
