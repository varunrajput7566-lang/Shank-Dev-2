import os
import sys
import urllib.request
import subprocess
from dotenv import load_dotenv

# Load environment variables securely from .env
load_dotenv()

def download_background(width, height):
    """Attempt to download a free background, fallback to a solid color on failure."""
    bg_file = "background.jpg"
    url = f"https://picsum.photos/{width}/{height}?random=1"
    
    try:
        print(f"[1/3] Fetching visual assets from {url}...")
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            with open(bg_file, 'wb') as f:
                f.write(response.read())
        print(" -> Background downloaded successfully.")
        return bg_file
    except Exception as e:
        print(f" -> [WARNING] Failed to fetch asset: {e}")
        print(" -> Executing Fault Tolerance: Generating solid color fallback.")
        # Fallback: Generates a deep blue 1-frame image using FFmpeg
        subprocess.run([
            "ffmpeg", "-f", "lavfi", "-i", f"color=c=0x1a1a2e:s={width}x{height}:d=1",
            "-frames:v", "1", "-y", bg_file
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return bg_file

def generate_audio_and_subs(script_path, voice):
    """Generate voiceover and perfectly synced subtitles via Edge TTS."""
    audio_file = "audio.mp3"
    subs_file = "subs.srt"
    
    print(f"[2/3] Generating Audio & Subtitles (Voice: {voice})...")
    cmd = [
        "edge-tts",
        "--file", script_path,
        "--voice", voice,
        "--write-media", audio_file,
        "--write-subtitles", subs_file
    ]
    
    try:
        subprocess.run(cmd, check=True)
        print(" -> Audio and SRT generated successfully.")
        return audio_file, subs_file
    except subprocess.CalledProcessError as e:
        print(f" -> [FATAL ERROR] Edge-TTS failed: {e}")
        sys.exit(1)

def render_video(bg_file, audio_file, subs_file, width, height, output_file="final_video.mp4"):
    """Compile the final video, looping the background and burning the subtitles."""
    print("[3/3] Compositing video via FFmpeg Engine...")
    
    # SubRip formatting for burned-in subtitles. 
    # Fontsize is relative; 24 is highly legible for 1080x1920 Shorts/Reels.
    style = "Fontname=Arial,FontSize=24,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=2,Alignment=2,MarginV=100"
    
    cmd = [
        "ffmpeg",
        "-loop", "1",                           # Loop the single image
        "-framerate", "30",                     # Standard web framerate
        "-i", bg_file,                          # Input 1: Visual
        "-i", audio_file,                       # Input 2: Audio
        # Scale to ensure exact dimensions, then burn in subtitles
        "-vf", f"scale={width}:{height},subtitles={subs_file}:force_style='{style}'",
        "-c:v", "libx264",                      # H.264 Video Codec
        "-preset", "fast",                      # Optimized for GitHub CPU Runners
        "-tune", "stillimage",                  # Improves compression for static backgrounds
        "-c:a", "aac",                          # AAC Audio Codec
        "-b:a", "192k",                         # High audio bitrate
        "-shortest",                            # Stop render when the audio track ends
        "-y",                                   # Overwrite output automatically
        output_file
    ]
    
    try:
        subprocess.run(cmd, check=True)
        print(f" -> Video rendered successfully: {output_file}")
    except subprocess.CalledProcessError as e:
        print(f" -> [FATAL ERROR] FFmpeg render failed: {e}")
        sys.exit(1)

def main():
    # Variables populated by GitHub Actions (.env)
    voice = os.getenv("TTS_VOICE", "en-IN-NeerjaNeural")
    width = os.getenv("VIDEO_WIDTH", "1080")
    height = os.getenv("VIDEO_HEIGHT", "1920")
    script_file = "script.txt"
    
    if not os.path.exists(script_file):
        print(f"[FATAL ERROR] Could not find script file: {script_file}")
        sys.exit(1)
        
    bg_file = download_background(width, height)
    audio_file, subs_file = generate_audio_and_subs(script_file, voice)
    render_video(bg_file, audio_file, subs_file, width, height)

if __name__ == "__main__":
    main()
