#!/usr/bin/env python

import os
import sys
import yt_dlp

def test_youtube_download(url):
    """Test downloading a YouTube video with proper cookies."""
    print(f"Testing YouTube download for URL: {url}")
    
    # Try different potential cookie paths
    cookie_paths = [
        os.path.join("app", "utils", "cookies.txt"),
        os.path.join("/app", "app", "utils", "cookies.txt"),
        "cookies.txt"
    ]
    
    # Check which cookie file exists
    cookie_file = None
    for path in cookie_paths:
        print(f"Checking cookie path: {path}")
        if os.path.exists(path):
            print(f"Cookie file found at: {path}")
            print(f"Cookie file size: {os.path.getsize(path)} bytes")
            cookie_file = path
            break
    
    if not cookie_file:
        print("No cookie file found!")
        return False
    
    # Configure YoutubeDL options
    ydl_opts = {
        'format': 'best',
        'cookiefile': cookie_file,
        'quiet': False,
        'verbose': True,
        'no_warnings': False,
        'ignoreerrors': False,
        'no_color': True,
    }
    
    print(f"Download options: {ydl_opts}")
    
    try:
        # First try listing formats
        print("\n--- Listing available formats ---")
        list_opts = ydl_opts.copy()
        list_opts['listformats'] = True
        
        with yt_dlp.YoutubeDL(list_opts) as ydl:
            ydl.extract_info(url, download=False)
        
        # Then try downloading
        print("\n--- Attempting download ---")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            
            if info:
                print(f"Successfully downloaded video: {info.get('title', 'Unknown')}")
                return True
            else:
                print("Failed to extract video info")
                return False
    except Exception as e:
        print(f"Error during download: {str(e)}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_youtube_download.py <youtube_url>")
        sys.exit(1)
    
    url = sys.argv[1]
    success = test_youtube_download(url)
    
    if success:
        print("\nDownload test SUCCESSFUL!")
        sys.exit(0)
    else:
        print("\nDownload test FAILED!")
        sys.exit(1) 