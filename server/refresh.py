#!/usr/bin/env python3

import os
import json
import google.auth.transport.requests
from google.oauth2.credentials import Credentials

# Path to your credentials.json (the file containing client_id, client_secret, and refresh_token)
CREDENTIALS_FILE = 'creds.storage'

def refresh_token():
    # Check if credentials file exists
    if os.path.exists(CREDENTIALS_FILE):
        with open(CREDENTIALS_FILE, 'r') as credentials_file:
            credentials_data = json.load(credentials_file)
    else:
        print(f'Credentials file "{CREDENTIALS_FILE}" not found.')
        return

    # Check if the necessary fields are present in the credentials file
    if 'client_id' not in credentials_data or 'client_secret' not in credentials_data or 'refresh_token' not in credentials_data:
        print('Missing required fields in credentials.json (client_id, client_secret, or refresh_token).')
        return

    # Create credentials object using refresh token from credentials.json
    credentials = Credentials(
        None,  # No access token initially
        refresh_token=credentials_data['refresh_token'],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=credentials_data['client_id'],
        client_secret=credentials_data['client_secret']
    )

    # Refresh the token
    try:
        request = google.auth.transport.requests.Request()
        credentials.refresh(request)
        print('Token refreshed successfully!')

        # Update the credentials data with the new access token and expiration time
        credentials_data['token'] = credentials.token
        credentials_data['expiry'] = credentials.expiry.isoformat() if credentials.expiry else None

        # Save the updated credentials back to the credentials.json file
        with open(CREDENTIALS_FILE, 'w') as credentials_file:
            json.dump(credentials_data, credentials_file, indent=4)
        print(f'Updated credentials saved to "{CREDENTIALS_FILE}".')

    except Exception as e:
        print(f'Error refreshing token: {e}')

if __name__ == "__main__":
    refresh_token()

