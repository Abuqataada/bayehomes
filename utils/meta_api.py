import os
import requests
from flask import current_app

def post_to_facebook(page_id, message, image_path=None, video_path=None):
    """Post to Facebook Page feed."""
    url = f"https://graph.facebook.com/{current_app.config['META_API_VERSION']}/{page_id}/feed"
    access_token = current_app.config['META_ACCESS_TOKEN']
    data = {'message': message, 'access_token': access_token}
    files = {}
    
    if image_path:
        files['source'] = open(image_path, 'rb')
        # Use photo endpoint for images
        url = f"https://graph.facebook.com/{current_app.config['META_API_VERSION']}/{page_id}/photos"
        data = {'caption': message, 'access_token': access_token}
        resp = requests.post(url, data=data, files=files)
    elif video_path:
        files['source'] = open(video_path, 'rb')
        url = f"https://graph.facebook.com/{current_app.config['META_API_VERSION']}/{page_id}/videos"
        data = {'description': message, 'access_token': access_token}
        resp = requests.post(url, data=data, files=files)
    else:
        resp = requests.post(url, data=data)
    
    if files:
        for f in files.values():
            f.close()
    return resp.json()

def post_to_instagram(ig_user_id, message, image_path=None, video_path=None):
    """Post to Instagram Business Account."""
    access_token = current_app.config['META_ACCESS_TOKEN']
    # Step 1: Create media container
    create_url = f"https://graph.facebook.com/{current_app.config['META_API_VERSION']}/{ig_user_id}/media"
    data = {'caption': message, 'access_token': access_token}
    
    if image_path:
        data['image_url'] = image_path  # Must be a public URL or use file upload – Meta requires URL
        # For simplicity, we assume image is already hosted; we'll use a simpler approach: direct file upload is not supported.
        # We'll require a public URL for images/videos for Instagram.
        # Alternative: use the 'media_type' and upload via URL.
        # We'll implement with hosted files.
        return {"error": "Instagram requires media URLs. Please upload to a cloud storage first."}
    elif video_path:
        data['video_url'] = video_path
    else:
        # Text-only posts are not supported on Instagram; need a media.
        return {"error": "Instagram posts require an image or video."}
    
    resp = requests.post(create_url, data=data)
    if resp.status_code != 200:
        return resp.json()
    container_id = resp.json().get('id')
    if not container_id:
        return {"error": "Failed to create container"}
    
    # Step 2: Publish the container
    publish_url = f"https://graph.facebook.com/{current_app.config['META_API_VERSION']}/{ig_user_id}/media_publish"
    publish_data = {'creation_id': container_id, 'access_token': access_token}
    resp = requests.post(publish_url, data=publish_data)
    return resp.json()
