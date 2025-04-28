# YouTube Cookies Setup Guide

This guide explains how to generate proper YouTube cookies for use with the yt-dlp downloader, which is necessary to download age-restricted videos, private videos, and avoid captchas.

## Option 1: Using the Cookie-Editor browser extension

1. Install the [Cookie-Editor](https://cookie-editor.cgagnier.ca/) extension for your browser:
   - [Chrome Web Store](https://chrome.google.com/webstore/detail/cookie-editor/hlkenndednhfkekhgcdicdfddnkalmdm)
   - [Firefox Add-ons](https://addons.mozilla.org/en-US/firefox/addon/cookie-editor/)

2. Login to your YouTube account at [youtube.com](https://www.youtube.com/)

3. Click on the Cookie-Editor extension icon in your browser toolbar

4. Click "Export" in the bottom right, and choose "Export as Netscape HTTP Cookie File"

5. Save the file as `cookies.txt` in the `app/utils/` directory of this project

## Option 2: Using yt-dlp's built-in browser cookie extraction

You can use yt-dlp directly to extract cookies from your browser:

```bash
# For Chrome/Chromium:
yt-dlp --cookies-from-browser chrome --cookies-file app/utils/cookies.txt

# For Firefox:
yt-dlp --cookies-from-browser firefox --cookies-file app/utils/cookies.txt

# For Edge:
yt-dlp --cookies-from-browser edge --cookies-file app/utils/cookies.txt

# For Safari:
yt-dlp --cookies-from-browser safari --cookies-file app/utils/cookies.txt
```

## Option 3: Using the provided scripts

This project includes two scripts to help with cookie management:

1. `fix_cookies.py` - Checks and fixes an existing cookie file to ensure compatibility with yt-dlp
   ```bash
   python fix_cookies.py [path_to_cookies.txt]
   ```

2. `test_youtube_download.py` - Tests if your cookies file works by downloading a YouTube video
   ```bash
   python test_youtube_download.py https://youtube.com/shorts/n-aXWFVMtL0
   ```

## Common Issues with YouTube Cookies

1. **Missing Critical Cookies**: YouTube authentication requires certain cookies like SID, HSID, SSID, etc.

2. **Incorrect Format**: The cookies file must be in Netscape HTTP Cookie File format.

3. **Cookie Expiration**: YouTube cookies typically expire after a certain period. If downloads fail, try generating fresh cookies.

4. **File Path**: Make sure the cookies file is in the correct location (`app/utils/cookies.txt`).

5. **File Permissions**: The cookies file must be readable by the application.

## Testing Your Cookies

Once you've created your cookies file, test it with:

```bash
python -m yt_dlp --cookies app/utils/cookies.txt "https://youtube.com/shorts/n-aXWFVMtL0" -f best --verbose
```

If successful, you'll see the download begin. If not, you'll see an error about being unable to authenticate.

## Using in Docker Environment

If you're running in a Docker environment, make sure the cookies file is included in your Docker image or mounted as a volume. The absolute path in the container would typically be `/app/app/utils/cookies.txt`. 