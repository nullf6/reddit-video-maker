from moviepy.editor import (
    CompositeAudioClip,
    concatenate_videoclips,
    VideoFileClip,
    CompositeVideoClip,
    AudioFileClip,
    ImageClip,
    TextClip,
    afx
)
import whisper_timestamped as whisper
from moviepy.video.fx.all import crop
import generate_voice
import fetch_data
import create_box
import random
from PIL import Image, ImageDraw

def create_masked_overlay(image_path, output_path, corner_radius=20, new_size=None):
    """Create a mask for the image to keep the blacks opaque and round the corners, with optional resizing."""
    image = Image.open(image_path).convert("RGBA")

    if new_size:
        image = image.resize(new_size, Image.Resampling.LANCZOS)  # Updated to use LANCZOS

    width, height = image.size

    # Create a rounded rectangle mask
    mask = Image.new("L", (width, height), 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle(
        [(0, 0), (width, height)], corner_radius, fill=255
    )

    # Apply the mask to the alpha channel
    image.putalpha(mask)
    image.save(output_path)

def get_text_clips(text):
    text_clips_array = []
    segments = text["segments"]

    for segment in segments:
        words = segment["words"]
        i = 0
        while i < len(words):
            # Group up to 3 words together
            word_group = words[i:i+3]
            text = " ".join([word["text"] for word in word_group])
            start_time = word_group[0]["start"]
            end_time = word_group[-1]["end"]

            text_clips_array.append(
                TextClip(
                    text,
                    fontsize=50,
                    stroke_color="Black",
                    color="White",
                    stroke_width=1,
                    font="Barlow-ExtraBold"
                ).set_start(start_time)
                .set_end(end_time)
                .set_position("center")
            )
            i += 3

    return text_clips_array


def create_tiktok_clip(
    background_video_path,
    background_music_path,
    voice1_path,
    voice2_path,
    overlay_image_path,
    output_path,
    overlay_size=None,
    animation_rate=0.4,
):
    # Load media files
    background_video = VideoFileClip(background_video_path)
    background_music = AudioFileClip(background_music_path)
    voice1 = AudioFileClip(voice1_path)
    voice2 = AudioFileClip(voice2_path)
    model = whisper.load_model("small", device="cpu")
    transcribed_text = whisper.transcribe(model, voice2_path, language='en')

    # Calculate total duration (intro + main clip)
    total_duration = voice1.duration + voice2.duration

    # Load the background video and select a random subclip
    if background_video.duration > total_duration:
        start_time = random.uniform(0, background_video.duration - total_duration)
        background_video = background_video.subclip(start_time, start_time + total_duration + 2)
    else:
        background_video = background_video.subclip(0, total_duration)

    # Crop the background video to 9:16 aspect ratio (TikTok's aspect ratio)
    (w, h) = background_video.size
    crop_width = h * 9 / 16
    x1, x2 = (w - crop_width) // 2, (w + crop_width) // 2
    y1, y2 = 0, h
    background_video = crop(background_video, x1=x1, y1=y1, x2=x2, y2=y2)

    # Prepare the masked overlay image
    masked_overlay_path = "masked_overlay.png"
    create_masked_overlay(overlay_image_path, masked_overlay_path, new_size=overlay_size)

    # Load and resize the overlay image
    overlay_image = ImageClip(masked_overlay_path).set_duration(voice1.duration)

    # Create a function to animate the size change from 95% to 100% over the specified animation rate
    def resize_func(t):
        scale = 0.95 + 0.05 * min(1, t / animation_rate)  # Linear scale from 0.95 to 1.0
        return overlay_image.size[0] * scale, overlay_image.size[1] * scale

    # Apply the resizing function and center the image
    overlay_image = overlay_image.resize(resize_func).set_position("center")

    # Create the intro clip with voice1 and the expanding overlay image
    intro_clip = CompositeVideoClip([background_video, overlay_image])
    intro_clip = intro_clip.set_audio(voice1).subclip(0, voice1.duration)

    # generating text clips and audio clip for intro
    text_clips = get_text_clips(transcribed_text)

    # Create the main clip with voice2 and the background video
    main_background = background_video.subclip(voice1.duration, total_duration)
    main_clip = CompositeVideoClip([main_background] + text_clips)
    main_clip = main_clip.set_audio(voice2)

    # Concatenate the intro and main clips
    final_clip = concatenate_videoclips([intro_clip, main_clip])

    # Loop background music for the entire duration
    background_music = afx.audio_loop(background_music, duration=total_duration)

    # Set background music to play throughout the video
    final_audio = CompositeAudioClip([background_music.volumex(0.5), final_clip.audio])
    final_clip = final_clip.set_audio(final_audio)

    # Output the final clip with high quality
    final_clip.write_videofile(output_path, codec="libx264", fps=24)

# Example usage
url = input("Enter the post URL: ")
post_title = fetch_data.getSubmissionTitle(url)
post_body = fetch_data.getSubmissionBody(url)
background_video_path = "../data/background_video.webm"
background_music_path = "../data/background_music/moments.m4a"
voice1_path = '../data/text_audio/example1.mp3'
voice2_path = '../data/text_audio/example2.mp3'
overlay_image_path = create_box.create_text_image_with_overlay(post_title, 20, "../data/logo.png", "lol.png")
output_path = "tiktok_video.mp4"
overlay_size = (600,156)  # Example size for resizing
animation_rate = 0.1  # Example animation rate

create_tiktok_clip(
    background_video_path,
    background_music_path,
    voice1_path,
    voice2_path,
    overlay_image_path,
    output_path,
    overlay_size=overlay_size,
    animation_rate=animation_rate,
)
