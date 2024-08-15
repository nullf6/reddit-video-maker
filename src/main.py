from moviepy.editor import (
    CompositeAudioClip,
    concatenate_videoclips,
    VideoFileClip,
    CompositeVideoClip,
    TextClip,
    AudioFileClip,
    ImageClip,
    concatenate_videoclips,
    concatenate_audioclips,
    afx
)
from moviepy.video.fx.resize import resize
from moviepy.video.fx.fadein import fadein
from moviepy.video.fx.fadeout import fadeout
import generate_voice
import fetch_data
import create_box
import random
import cv2
from moviepy.video.fx.all import crop

def create_tiktok_clip(
    background_video_path,
    background_music_path,
    voice1_path,
    voice2_path,
    overlay_image_path,
    output_path,
):
    # Load media files
    background_video = VideoFileClip(background_video_path)

    background_music = AudioFileClip(background_music_path)
    voice1 = AudioFileClip(voice1_path)
    voice2 = AudioFileClip(voice2_path)

    # Calculate total duration (intro + main clip)
    total_duration = voice1.duration + voice2.duration

    # Load the background video and select a random subclip
    background_video = VideoFileClip(background_video_path)

    if background_video.duration > total_duration:
        start_time = random.uniform(0, background_video.duration - total_duration)
        background_video = background_video.subclip(start_time, start_time + total_duration)
    else:
        background_video = background_video.subclip(0, total_duration)

    # Cropping background video to 9:16 aspect ratio (TikTok's aspect ratio)
    (w, h) = background_video.size
    crop_width = h * 9/16
    x1, x2 = (w - crop_width)//2, (w + crop_width)//2
    y1, y2 = 0, h
    background_video = crop(background_video, x1=x1, y1=y1, x2=x2, y2=y2)

    # Generate the overlay image clip and adjust the size
    overlay_image = ImageClip(overlay_image_path)
    overlay_image = overlay_image.set_duration(voice1.duration)
    overlay_image = overlay_image.resize(height=80).set_position("center")  # Adjust the height to fit better

    # Create the intro clip with voice1 and the expanding overlay image
    intro_clip = CompositeVideoClip([background_video, overlay_image])
    intro_clip = intro_clip.set_audio(voice1).subclip(0, voice1.duration)

    # Create the main clip with voice2 and the background video
    main_clip = background_video.set_audio(voice2).subclip(0, voice2.duration)

    # Concatenate the intro and main clips
    final_clip = concatenate_videoclips([intro_clip, main_clip])

    # Loop background music for the entire duration
    background_music = afx.audio_loop(background_music, duration=total_duration)

    # Set background music to play throughout the video
    final_audio = CompositeAudioClip([background_music.volumex(0.5), final_clip.audio])
    final_clip = final_clip.set_audio(final_audio)

    # Output the final clip with high quality
    final_clip.write_videofile(output_path, codec="libx264", fps=24, bitrate="3000k", audio_codec="aac")

url = input("Enter the post url: ")
post_title = fetch_data.getSubmissionTitle(url)
post_body = fetch_data.getSubmissionBody(url)
background_video_path = "../data/background_video.mp4"
background_music_path = "../data/background_music/moments.m4a"
voice1_path = generate_voice.getTextAudio("example1", post_title)
voice2_path = generate_voice.getTextAudio("example2", post_body)
overlay_image_path = create_box.create_text_image_with_overlay(post_title, 20, "../data/logo.png", "lol.png")
output_path = "tiktok_video.mp4"

create_tiktok_clip(
    background_video_path,
    background_music_path,
    voice1_path,
    voice2_path,
    overlay_image_path,
    output_path,
)
