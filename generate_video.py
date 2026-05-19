import os
import re
import subprocess
import textwrap
from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips
from PIL import Image, ImageDraw, ImageFont

# 1. Fetch the script from GitHub Actions environment variables
script_text = os.environ.get("VIDEO_SCRIPT", "This is a default test video. The pipeline is running perfectly.")
resolution = (1080, 1920) # 9:16 format for Shorts/Reels

# 2. Language & Voice Auto-Detection
def is_hindi(text):
    # Checks for Devanagari script characters
    return any("\u0900" <= c <= "\u097F" for c in text)

# Madhur is a male Hindi voice; Prabhat is a male Indian-English voice (excellent for Hinglish)
voice = "hi-IN-MadhurNeural" if is_hindi(script_text) else "en-IN-PrabhatNeural"
print(f"Detected Language. Using voice: {voice}")

# 3. Generate Audio via edge-tts
print("Generating TTS Audio...")
subprocess.run([
    "edge-tts", 
    "--voice", voice, 
    "--text", script_text, 
    "--write-media", "audio.mp3"
], check=True)

audio_clip = AudioFileClip("audio.mp3")
total_duration = audio_clip.duration

# 4. Fault-Tolerant Visual Generation
def create_frame(text, output_path, bg_color=(20, 20, 25)):
    """Generates a solid image frame with centered wrapped text."""
    img = Image.new('RGB', resolution, color=bg_color)
    draw = ImageDraw.Draw(img)
    
    # Graceful fallback font loading (Noto handles English and Hindi)
    font_path = "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf" if is_hindi(text) else "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf"
    try:
        font = ImageFont.truetype(font_path, 65)
    except IOError:
        font = ImageFont.load_default()

    # Wrap and center text dynamically
    lines = textwrap.wrap(text, width=25)
    y_text = (resolution[1] // 2) - (len(lines) * 45)
    
    for line in lines:
        # PIL 8.0.0+ bounding box logic
        bbox = draw.textbbox((0, 0), line, font=font)
        w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.text(((resolution[0] - w) // 2, y_text), line, font=font, fill=(255, 255, 255))
        y_text += h + 25

    img.save(output_path)

# 5. Synchronize Text Chunks with Audio
# Split script into readable chunks based on punctuation
chunks = [s.strip() for s in re.split(r'[.!?]+', script_text) if s.strip()]
if not chunks:
    chunks = [script_text]

chunk_duration = total_duration / len(chunks)
clips = []

print(f"Creating {len(chunks)} video frames...")
for i, chunk in enumerate(chunks):
    frame_path = f"frame_{i}.jpg"
    create_frame(chunk, frame_path)
    
    # Create an image clip lasting exactly the length required for the audio sync
    clip = ImageClip(frame_path).set_duration(chunk_duration)
    clips.append(clip)

# 6. Final Rendering
print("Concatenating video components...")
video = concatenate_videoclips(clips, method="compose")
video = video.set_audio(audio_clip)

print("Rendering final MP4...")
video.write_videofile(
    "final_video.mp4", 
    fps=24, 
    codec="libx264", 
    audio_codec="aac",
    preset="ultrafast",   # Crucial for CPU runtime limits
    threads=4             # Utilizes full GitHub Action runner cores
)

# Cleanup temporary frames
for i in range(len(chunks)):
    os.remove(f"frame_{i}.jpg")
os.remove("audio.mp3")

print("Pipeline execution complete. Video saved as final_video.mp4")
