#!/usr/bin/env python3 

from simple_youtube_api.Channel import Channel
from simple_youtube_api.LocalVideo import LocalVideo
import sys

# loggin into the channel
channel = Channel()
#creds.storage is for the upload
#credentials.storage is for storing the refresh token info used my ./refresh.py

channel.login("client_secret.json", "creds.storage")

# setting up the video that is going to be uploaded
video = LocalVideo(file_path="video-out/last.mp4")

# setting snippet
video.set_title("Daily Recap " + sys.argv[1])
video.set_description("Automated Upload")
video.set_tags(["marmot", "time-lapse"])
#video.set_category("gaming")
video.set_default_language("en-US")

# setting status
video.set_embeddable(True)
video.set_license("creativeCommon")
video.set_privacy_status("public")
video.set_public_stats_viewable(True)

# setting thumbnail
#video.set_thumbnail_path('test_thumb.png')

# uploading video and printing the results
video = channel.upload_video(video)
print(video.id)
print(video)

# liking video
video.like()
