#!/usr/bin/env python3

import json
import google.auth.transport.requests
import requests
import google.oauth2.credentials

f = open('./creds.storage')
data = json.load(f)
f.close()

for i in data:
    print(f"{i} - {data[i]}")

#credentials = google.oauth2.credentials.Credentials('./credentials.storage')
credentials = google.oauth2.credentials.Credentials(
    token=data['access_token'],
    refresh_token=data['refresh_token'],
    token_uri=data['token_uri'],
    client_id=data['client_id'],
    client_secret=data['client_secret'],
    scopes=data['scopes'],
    
    )

print(f"access token: {credentials.token}")
print(credentials.expiry)

request = google.auth.transport.requests.Request()
credentials.refresh(request)

print(f"access token: {credentials.token}")
print(credentials.expiry)
json_token = json.loads(credentials.to_json())
for k in ['_module', '_class', 'user_agent', 'invalid']:
    print("assigning "+k)
    json_token[k] = data[k]
json_token['access_token'] = json_token['token']
json_token['token_expiry'] = json_token['expiry']
f = open("./creds.storage", "w")
f.write(json.dumps(json_token))
f.close()