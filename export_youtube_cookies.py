#!/usr/bin/env python

import os
import sys
import json
import time
import datetime
import subprocess
from pathlib import Path

# Default cookie file path
DEFAULT_COOKIE_PATH = os.path.join("app", "utils", "cookies.txt")

def print_header():
    print("=" * 60)
    print("YouTube Cookie Exporter for yt-dlp")
    print("=" * 60)
    print("This script will help export YouTube cookies directly from your browser")
    print("=" * 60)
    print()

def get_browser_choice():
    print("Select your browser:")
    print("1. Chrome/Chromium")
    print("2. Firefox")
    print("3. Edge")
    print("4. Safari")
    print("5. Opera")
    print("6. Brave")
    
    while True:
        choice = input("\nEnter number (1-6): ").strip()
        if choice in ["1", "2", "3", "4", "5", "6"]:
            return {
                "1": "chrome",
                "2": "firefox",
                "3": "edge",
                "4": "safari", 
                "5": "opera",
                "6": "brave"
            }[choice]
        print("Invalid choice. Please try again.")

def get_profile_choice(browser):
    print("\nDo you want to specify a browser profile?")
    print("1. Use default profile")
    print("2. Specify profile name/path")
    
    choice = input("\nEnter choice (1-2): ").strip()
    if choice == "2":
        profile = input(f"\nEnter {browser} profile name or path: ").strip()
        return profile
    return None

def get_output_path():
    print("\nWhere do you want to save the cookies?")
    print(f"1. Default location ({DEFAULT_COOKIE_PATH})")
    print("2. Specify a different location")
    
    choice = input("\nEnter choice (1-2): ").strip()
    if choice == "2":
        path = input("\nEnter full path for cookies file: ").strip()
        return path
    return DEFAULT_COOKIE_PATH

def export_cookies(browser, profile, output_path):
    cmd = ["yt-dlp", "--cookies-from-browser", browser]
    
    # Add profile if specified
    if profile:
        cmd.extend(["--browser-profile", profile])
    
    # Add output file
    cmd.extend(["--cookies", output_path])
    
    # Add a test URL to make yt-dlp happy
    cmd.append("https://youtube.com/watch?v=jNQXAC9IVRw")  # First YouTube video ever
    
    # Add dry-run to avoid actual download
    cmd.append("--skip-download")
    
    print("\nExecuting command:", " ".join(cmd))
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            if os.path.exists(output_path):
                size = os.path.getsize(output_path)
                print(f"\nSuccess! Cookies exported to: {output_path}")
                print(f"File size: {size} bytes")
                
                # Check if file size is suspiciously small
                if size < 1000:
                    print("\nWARNING: Cookie file is very small. It might not contain all required cookies.")
                    print("Make sure you're logged into YouTube in your browser.")
                
                return True
            else:
                print(f"\nError: Cookie file wasn't created at {output_path}")
                return False
        else:
            print("\nError executing yt-dlp command:")
            print(result.stderr)
            return False
    except Exception as e:
        print(f"\nError: {str(e)}")
        return False

def verify_cookies(cookie_path):
    print("\nVerifying cookies file...")
    
    if not os.path.exists(cookie_path):
        print(f"Error: Cookie file not found at {cookie_path}")
        return False
    
    file_size = os.path.getsize(cookie_path)
    if file_size < 1000:
        print(f"Warning: Cookie file is very small ({file_size} bytes)")
        print("The cookies might not be complete.")
    
    try:
        with open(cookie_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for Netscape format header
        if not content.startswith("# Netscape HTTP Cookie File"):
            print("Warning: Cookie file doesn't have the correct format header")
        
        # Count cookies
        cookie_count = sum(1 for line in content.splitlines() if line.strip() and not line.startswith('#'))
        print(f"Found {cookie_count} cookies in the file")
        
        # Check for important YouTube cookies
        important_cookies = ['SID', 'HSID', 'SSID', 'APISID', 'SAPISID']
        found_important = []
        
        for cookie in important_cookies:
            if cookie in content:
                found_important.append(cookie)
        
        if found_important:
            print(f"Found these important cookies: {', '.join(found_important)}")
        else:
            print("Warning: No important YouTube cookies found")
            
        # Test with a simple yt-dlp command
        print("\nTesting cookies with yt-dlp...")
        test_cmd = ["yt-dlp", "--cookies", cookie_path, "https://youtube.com/watch?v=jNQXAC9IVRw", "--skip-download", "--no-warnings"]
        
        result = subprocess.run(test_cmd, capture_output=True, text=True)
        if "Please sign in" in result.stderr:
            print("Warning: Test failed - YouTube still requires sign in")
            print("Your cookies might be expired or incomplete")
            return False
        else:
            print("Test succeeded! Cookies appear to be working.")
            return True
        
    except Exception as e:
        print(f"Error verifying cookies: {str(e)}")
        return False

def make_backup(cookie_path):
    if os.path.exists(cookie_path):
        backup_path = f"{cookie_path}.bak.{int(time.time())}"
        try:
            with open(cookie_path, 'r', encoding='utf-8') as src:
                with open(backup_path, 'w', encoding='utf-8') as dst:
                    dst.write(src.read())
            print(f"Created backup at: {backup_path}")
            return True
        except Exception as e:
            print(f"Warning: Could not create backup: {str(e)}")
            return False
    return False

if __name__ == "__main__":
    print_header()
    
    # Make sure yt-dlp is installed
    try:
        subprocess.run(["yt-dlp", "--version"], capture_output=True, check=True)
    except (subprocess.SubprocessError, FileNotFoundError):
        print("Error: yt-dlp is not installed or not in PATH")
        print("Please install it with: pip install yt-dlp")
        sys.exit(1)
    
    # Get user inputs
    browser = get_browser_choice()
    profile = get_profile_choice(browser)
    output_path = get_output_path()
    
    # Make backup of existing file
    if os.path.exists(output_path):
        make_backup(output_path)
    
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    
    # Export cookies
    if export_cookies(browser, profile, output_path):
        verify_cookies(output_path)
        print("\nProcess completed.")
    else:
        print("\nFailed to export cookies.")
        sys.exit(1)
    
    print("\nYou can now use these cookies with yt-dlp or in the API.")
    print(f"\nCookie file path: {os.path.abspath(output_path)}") 