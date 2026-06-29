#!/usr/bin/env python3 

from simple_youtube_api.Channel import Channel
from simple_youtube_api.LocalVideo import LocalVideo
import sys

# Work around a bug in simple_youtube_api's progress bar: it calls
# bar.update(100 * 10 * progress + 1) against a bar with max_value=1000, so the
# trailing +1 overflows the range once progress > 0.999 and raises ValueError,
# killing the upload near 100%. Clamp update() to the bar's max_value.
import progressbar
_orig_update = progressbar.ProgressBar.update
def _clamped_update(self, value=None, *a, **k):
    if value is not None and self.max_value is not None:
        value = min(value, self.max_value)
    return _orig_update(self, value, *a, **k)
progressbar.ProgressBar.update = _clamped_update

# loggin into the channel
channel = Channel()
#creds.storage is for the upload
#credentials.storage is for storing the refresh token info used my ./refresh.py

channel.login("client_secret.json", "creds.storage")

# setting up the video that is going to be uploaded
video = LocalVideo(file_path="video-out/last.mp4")

description = """If you're going to buy something on Amazon, use my affiliate link and send me a nail to bend at no cost to you:

https://amzn.to/4aAUsXc

Any purchase you make through this link helps out the build!

0:13 - sunrise"""

# setting snippet
video.set_title("Daily Recap " + sys.argv[1])
video.set_description(description)
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
