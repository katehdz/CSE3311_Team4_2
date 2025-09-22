# Secrets Directory

This directory contains sensitive configuration files that should never be committed to version control.

## Setup Instructions

1. Copy `serviceAccountKey.json.json.example` to `serviceAccountKey.json.json`
2. Replace the placeholder values with your actual Firebase service account credentials
3. Make sure the path in your `.env` file points to this file

## Security Notes

- The actual `serviceAccountKey.json.json` file is ignored by git (see `.gitignore`)
- Never commit actual credentials to version control
- Keep your service account key secure and don't share it publicly
- If you accidentally expose credentials, revoke them immediately from the Google Cloud Console

## Getting Firebase Credentials

1. Go to the [Firebase Console](https://console.firebase.google.com/)
2. Select your project
3. Go to Project Settings > Service Accounts
4. Click "Generate new private key"
5. Save the downloaded file as `serviceAccountKey.json.json` in this directory
