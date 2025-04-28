#!/usr/bin/env python

import os
import sys
import re
import http.cookiejar

def fix_youtube_cookies(input_file, output_file=None):
    """
    Check and fix YouTube cookie file to ensure compatibility with yt-dlp.
    
    Args:
        input_file: Path to the input cookies file
        output_file: Path to save the fixed cookies (defaults to input_file if None)
    
    Returns:
        bool: True if successful, False otherwise
    """
    if not output_file:
        output_file = input_file
    
    if not os.path.exists(input_file):
        print(f"Error: Cookie file not found at {input_file}")
        return False
    
    print(f"Processing cookie file: {input_file}")
    print(f"File size: {os.path.getsize(input_file)} bytes")
    
    try:
        # Try to read the file content
        with open(input_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
        lines = content.strip().split('\n')
        print(f"File contains {len(lines)} lines")
        
        # Check if it's likely a Netscape format cookie file
        if not content.startswith("# Netscape HTTP Cookie File"):
            print("Warning: File doesn't appear to be in Netscape format")
            print("First few lines:")
            for line in lines[:5]:
                print(f"  {line}")
            
            # Try to convert to Netscape format
            if "HTTP Cookie File" not in content:
                print("Adding Netscape cookie file header...")
                content = "# Netscape HTTP Cookie File\n# http://curl.haxx.se/rfc/cookie_spec.html\n# This is a generated file! Do not edit.\n\n" + content
        
        # Ensure YouTube domains are included
        domains = set()
        for line in lines:
            if line.strip() and not line.startswith('#'):
                parts = line.split('\t')
                if len(parts) >= 2:
                    domains.add(parts[0])
        
        print(f"Domains in cookie file: {', '.join(domains)}")
        
        youtube_domains = {'.youtube.com', 'youtube.com', '.google.com', 'google.com'}
        missing_domains = youtube_domains - domains
        
        if missing_domains:
            print(f"Warning: Missing important domains: {', '.join(missing_domains)}")
        
        # Check for critical cookies
        critical_cookies = {'SID', 'HSID', 'SSID', 'APISID', 'SAPISID', '__Secure-1PSID', '__Secure-3PSID'}
        found_cookies = set()
        
        for line in lines:
            if line.strip() and not line.startswith('#'):
                parts = line.split('\t')
                if len(parts) >= 7:
                    cookie_name = parts[5]
                    if cookie_name in critical_cookies:
                        found_cookies.add(cookie_name)
        
        missing_cookies = critical_cookies - found_cookies
        if missing_cookies:
            print(f"Warning: Missing critical cookies: {', '.join(missing_cookies)}")
        else:
            print("All critical cookies are present")
        
        # Write the fixed file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"Cookie file processed and saved to: {output_file}")
        return True
    
    except Exception as e:
        print(f"Error processing cookie file: {str(e)}")
        return False

if __name__ == "__main__":
    # Check if the cookies file exists in common locations
    cookie_paths = [
        os.path.join("app", "utils", "cookies.txt"),
        os.path.join("/app", "app", "utils", "cookies.txt"),
        "cookies.txt"
    ]
    
    found_path = None
    for path in cookie_paths:
        if os.path.exists(path):
            print(f"Found cookies file at: {path}")
            found_path = path
            break
    
    if not found_path:
        print("No cookies file found in standard locations")
        if len(sys.argv) > 1:
            found_path = sys.argv[1]
            print(f"Using provided path: {found_path}")
        else:
            print("Please provide the path to your cookies file as an argument")
            sys.exit(1)
    
    success = fix_youtube_cookies(found_path)
    
    if success:
        print("\nCookie file check/fix completed successfully!")
        sys.exit(0)
    else:
        print("\nCookie file check/fix failed!")
        sys.exit(1) 