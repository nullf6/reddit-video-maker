import os
import json
from moviepy.editor import (
    CompositeAudioClip,
    concatenate_videoclips,
    VideoFileClip,
    CompositeVideoClip,
    AudioFileClip,
    ImageClip,
    TextClip,
    afx,
    vfx
)
import whisper_timestamped as whisper
from moviepy.video.fx.all import crop
# import generate_voice
import fetch_data
import create_box
import random
from PIL import Image, ImageDraw
from tiktokvoice import tts
from audiostretchy.stretch import stretch_audio


def change_voice_pacing(voice_path, speed=0.8):
    new_path = f"{os.path.splitext(voice_path)[0]}_speed{os.path.splitext(voice_path)[1]}"
    stretch_audio(voice_path, new_path, speed)
    return new_path



# Paths to store the metadata
FINISHED_VIDEOS_PATH = "../data/finished_vids/finished_videos.json"
AUDIO_FILES_PATH = "../data/finished_vids/audio_files.json"

# Ensure the finished_vids directory exists
os.makedirs("../data/finished_vids", exist_ok=True)

def load_json(filepath):
    """Load JSON data from a file, or return an empty dictionary if the file doesn't exist."""
    if os.path.exists(filepath):
        with open(filepath, "r") as file:
            return json.load(file)
    return {}

def save_json(filepath, data):
    """Save JSON data to a file."""
    with open(filepath, "w") as file:
        json.dump(data, file, indent=4)

# Load existing data
finished_videos = load_json(FINISHED_VIDEOS_PATH)
audio_files = load_json(AUDIO_FILES_PATH)

def create_masked_overlay(image_path, output_path, corner_radius=20, new_size=None):
    """Create a mask for the image to keep the blacks opaque and round the corners, with optional resizing."""
    image = Image.open(image_path).convert("RGBA")

    if new_size:
        image = image.resize(new_size, Image.Resampling.LANCZOS)

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
            # Group up to 2 words together, with most instances being 1 word
            word_group = words[i:i+2] if random.random() < 0.3 else words[i:i+1]
            text = " ".join([word["text"] for word in word_group])
            start_time = word_group[0]["start"]
            end_time = word_group[-1]["end"]

            # Create the shadow clip
            shadow_clip = TextClip(
                text,
                font="Montserrat-ExtraBold",
                fontsize=70,
                color="black",
                stroke_color="black",
                stroke_width=10,
            ).set_start(start_time).set_end(end_time)

            shadow_clip = shadow_clip.fx(vfx.supersample, d=1.5, nframes=3)

            # Create the main text clip
            text_clip = TextClip(
                text,
                font="Montserrat-ExtraBold",
                fontsize=70,
                color="white",
            ).set_start(start_time).set_end(end_time)

            # Define the bounce effect function
            def bounce(t):
                return 1.1 + 0.1 * (1 - (t / 0.1)**2) if t <= 0.1 else 1

            shadow_clip = shadow_clip.resize(lambda t: bounce(t)).set_position('center')
            text_clip = text_clip.resize(lambda t: bounce(t)).set_position('center')

            final_text_clip = CompositeVideoClip([shadow_clip, text_clip])
            final_text_clip = final_text_clip.set_position("center", "center")
            text_clips_array.append(final_text_clip)

            i += len(word_group)

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
    url=None,
    post_title=None,
    post_body=None,
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
        scale = 0.95 + 0.05 * min(1, t / animation_rate)
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
    final_clip = concatenate_videoclips([intro_clip, main_clip], method="compose")

    # Loop background music for the entire duration
    background_music = afx.audio_loop(background_music, duration=total_duration)

    # Set background music to play throughout the video
    final_audio = CompositeAudioClip([background_music.volumex(0.1), final_clip.audio])
    final_clip = final_clip.set_audio(final_audio)

    # Output the final clip with high quality
    final_clip.write_videofile(output_path, codec="libx264", fps=60)

    # Update the finished videos and audio files records
    finished_videos[output_path] = {"url": url, "title": post_title, "output": output_path}
    audio_files[voice1_path] = post_title
    audio_files[voice2_path] = post_body

    # Save the updated data
    save_json(FINISHED_VIDEOS_PATH, finished_videos)
    save_json(AUDIO_FILES_PATH, audio_files)

def main():
    urls = []
    while True:
        url = input("Enter the post URL (or type 'done' to finish): ")
        if url.lower() == 'done':
            break
        urls.append(url)

    background_video_path = "../data/background_video4.webm"
    music_choice = {
        1: "../data/background_music/undertale.m4a",
        2: "../data/background_music/remix.m4a",
        3: "../data/background_music/undertale_shop.m4a",
        4: "../data/background_music/solitude.m4a",
        5: "../data/background_music/israel.m4a",
        6: "../data/background_music/up_theme.mp3"
    }

    try:
        choice = int(input("Choose your music. \n1. Undertale \n2. Remix \n3. Undertale Shop \n4. M83 - Solitude \n5. Israel\n6. Up Theme song \nEnter your input: "))
        background_music_path = music_choice.get(choice, "Invalid option, please select a valid option")
    except ValueError:
        print("Invalid input. Please enter a number.")
        return

    for i, url in enumerate(urls):
        post_title = fetch_data.getSubmissionTitle(url)
        post_body = fetch_data.getSubmissionBody(url)
        # voice1_path = generate_voice.getTextAudio(f'example1_{i}.mp3', post_title)
        # voice2_path = generate_voice.getTextAudio(f'example2_{i}.mp3', post_body)
        print("generating title voice..")
        voice1_path = tts(post_title, "en_us_010", f"../data/text_audio/postVoice_{i}.mp3")
        # voice2_path = tts(post_body, "en_us_010", f"../data/text_audio/bodyVoice_{i}.mp3")
        # voice1_path = tts(post_title, "en_us_010", f"../data/text_audio/postVoice_{i}.mp3")
        # change_voice_pacing(voice1_path, speed=1.5)
        voice2_path = tts(post_body, "en_us_010", f"../data/text_audio/bodyVoice_{i}.mp3")
        voice2_path = change_voice_pacing(voice2_path, speed=0.8)
        print("generating body voice..")
        overlay_image_path = create_box.create_text_image_with_overlay(post_title, 20, "../data/logo.png", f"lol_{i}.png")
        output_path = f"tiktok2_video_{i}.mp4"
        overlay_size = (round(500*1.2), round(overlay_image_path[1]*1.2))  # Example size for resizing
        animation_rate = 0.1  # Example animation rate

        create_tiktok_clip(
            background_video_path,
            background_music_path,
            voice1_path,
            voice2_path,
            overlay_image_path[0],
            output_path,
            overlay_size=overlay_size,
            animation_rate=animation_rate,
            url=url,
            post_title=post_title,
            post_body=post_body,
        )

if __name__ == "__main__":
    main()
