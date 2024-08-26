import re
from moviepy.editor import (
    CompositeAudioClip,
    concatenate_videoclips,
    VideoFileClip,
    CompositeVideoClip,
    AudioFileClip,
    ImageClip,
    TextClip,
    afx,
)
import whisper_timestamped as whisper
from moviepy.video.fx.all import crop
from tiktokvoice import tts
from audiostretchy.stretch import stretch_audio
from PIL import Image, ImageDraw
import os
import random
import fetch_data
import create_box

os.environ["FFMPEG_BINARY"] = "/usr/bin/ffmpeg"


def change_voice_pacing(voice_path, speed=0.85):
    new_path = f"{os.path.splitext(voice_path)[0]}_speed{speed}{os.path.splitext(voice_path)[1]}"
    stretch_audio(voice_path, new_path, speed)
    return new_path

def create_masked_overlay(image_path, output_path, corner_radius=20, new_size=None):
    """Create a mask for the image to keep the blacks opaque and round the corners, with optional resizing."""
    with Image.open(image_path).convert("RGBA") as image:
        if new_size:
            image = image.resize(new_size, Image.Resampling.LANCZOS)

        width, height = image.size
        mask = Image.new("L", (width, height), 0)
        draw = ImageDraw.Draw(mask)
        draw.rounded_rectangle((0, 0, width, height), corner_radius, fill=255)
        image.putalpha(mask)
        image.save(output_path)

def get_text_clips(transcribed_text):
    text_clips = []
    bounce = lambda t: 1.1 + 0.1 * (1 - (t / 0.1)**2) if t <= 0.1 else 1

    for segment in transcribed_text["segments"]:
        words = segment["words"]
        i = 0
        while i < len(words):
            word_group = words[i:i+2] if random.random() < 0.3 else words[i:i+1]
            text = " ".join(word["text"] for word in word_group)
            start_time, end_time = word_group[0]["start"], word_group[-1]["end"]

            shadow_clip = (TextClip(text, font="Montserrat-ExtraBold", fontsize=90, color="black", stroke_color="black", stroke_width=10)
                           .set_start(start_time).set_end(end_time)
                           .resize(lambda t: bounce(t)).set_position('center'))

            text_clip = (TextClip(text, font="Montserrat-ExtraBold", fontsize=90, color="white")
                         .set_start(start_time).set_end(end_time)
                         .resize(lambda t: bounce(t)).set_position('center'))

            text_clips.append(CompositeVideoClip([shadow_clip, text_clip]).set_position("center", "center"))
            i += len(word_group)

    return text_clips

def parse_text(text):
    """Parses and replaces abbreviations and age-gender formats, including those inside brackets."""
    replacements = {
        r'\bAITA\b': 'Am I the Asshole?',
        r'\bTIFU\b': 'Today I Fucked Up',
        r'\bpussy\b': 'coochie',
        r'\bF(\d{2})\b': r'Female \1',
        r'\bM(\d{2})\b': r'Male \1',
        r'\b(\d{2})F\b': r'Female \1',
        r'\b(\d{2})M\b': r'Male \1',
        r'\((\d{2})F\)': r'(Female \1)',
        r'\((\d{2})M\)': r'(Male \1)',
        r'\(F(\d{2})\)': r'(Female \1)',
        r'\(M(\d{2})\)': r'(Male \1)'
    }

    for pattern, repl in replacements.items():
        text = re.sub(pattern, repl, text)

    return text

def censor_text(text):
    """Censors specific words by replacing parts of them with asterisks."""
    censored_words = {
        r'\bfuck\b': 'f*ck',
        r'\bshit\b': 'sh*t',
        r'\basshole\b': 'a**hole',
        r'\bbitch\b': 'b*tch',
        r'\bcondom\b': 'c*ndom',
        r'\bpussy\b' : 'p*ssy',
        r'\bdamn\b': 'd*mn',
        r'\bhell\b': 'h*ll',
    }

    for word, censored in censored_words.items():
        text = re.sub(word, censored, text, flags=re.IGNORECASE)

    return text


def create_tiktok_clip(background_video_path, background_music_path, voice1_path, voice2_path,
                       overlay_image_path, output_path, overlay_size=None, animation_rate=0.4):
    # Load media files
    background_video = VideoFileClip(background_video_path)
    background_music = AudioFileClip(background_music_path)
    voice1 = AudioFileClip(voice1_path)
    voice2 = AudioFileClip(voice2_path)

    # Transcribe voice2 for text clips
    model = whisper.load_model("medium", device="cpu")
    transcribed_text = whisper.transcribe(model, voice2_path, language='en')

    # Calculate total duration (ending 1 second after the body voice ends)
    total_duration = voice1.duration + voice2.duration + 2  # Add 1 second after voice2 ends

    # Ensure the background video fits within the total duration
    start_time = random.uniform(0, background_video.duration - total_duration)
    background_video = background_video.subclip(start_time, start_time + total_duration)

    # Crop background video to 9:16 aspect ratio
    background_video = crop(background_video, width=background_video.h * 9 / 16, height=background_video.h, x_center=background_video.w / 2)

    # Prepare the masked overlay image
    masked_overlay_path = "masked_overlay.png"
    create_masked_overlay(overlay_image_path, masked_overlay_path, new_size=overlay_size)
    overlay_image = ImageClip(masked_overlay_path).set_duration(voice1.duration)

    # Animate overlay image resizing
    overlay_image = overlay_image.resize(lambda t: 0.95 + 0.05 * min(1, t / animation_rate)).set_position("center")

    # Create intro clip
    intro_background = background_video.subclip(0, voice1.duration)
    intro_clip = CompositeVideoClip([intro_background, overlay_image]).set_audio(voice1)

    # Generate text clips for the main clip
    text_clips = get_text_clips(transcribed_text)

    # Create the main clip
    main_background = background_video.subclip(voice1.duration, total_duration)  # Ensure this ends at total_duration
    main_clip = CompositeVideoClip([main_background] + text_clips).set_audio(voice2)

    # Concatenate intro and main clips
    final_clip = concatenate_videoclips([intro_clip, main_clip])

    # Loop background music and add it to the final clip
    background_music = afx.audio_loop(background_music, duration=total_duration)
    final_audio = CompositeAudioClip([background_music.volumex(0.15), final_clip.audio])
    final_audio = final_audio.subclip(0, final_audio.duration - 0.5)
    finished_clip = final_clip.set_audio(final_audio)

    # Output the final video
    finished_clip.write_videofile(output_path, codec="libx264", fps=60)

def process_videos(urls):
    for url in urls:
        submission_id = fetch_data.getSubmissionID(url)
        post_title = fetch_data.getSubmissionTitle(url)
        overlay_image_path = create_box.create_text_image_with_overlay(censor_text(post_title), 20, "../data/logo.png", "lol.png")
        post_title = parse_text(post_title)
        post_body = parse_text(fetch_data.getSubmissionBody(url))
        background_video_path = "../data/background_video.webm"
        background_music_path = "../data/background_music/up_theme.mp3"
        voice1_path = tts(post_title, "en_us_010", f"../data/text_audio/postVoice_{submission_id}.mp3")
        voice2_path = tts(post_body, "en_us_010", f"../data/text_audio/bodyVoice_{submission_id}.mp3")
        voice2_path = change_voice_pacing(voice2_path, speed=0.85)
        overlay_size = (round(500 * 1.9), round(overlay_image_path[1] * 1.9))
        output_path = f"../data/finished_vids/{submission_id}_video.mp4"

        create_tiktok_clip(
            background_video_path,
            background_music_path,
            voice1_path,
            voice2_path,
            overlay_image_path[0],
            output_path,
            overlay_size=overlay_size,
            animation_rate=0.1,
        )

def input_urls():
    urls = []
    while True:
        url = input("Enter a Reddit post URL (or 'done' to finish): ")
        if url.lower() == 'done':
            break
        elif url.startswith("https://www.reddit.com"):
            urls.append(url)
        else:
            print("Invalid URL. Please enter a valid Reddit post URL.")
    return urls

# Example usage
if __name__ == "__main__":
    print("Welcome to the TikTok video generator!")
    urls = input_urls()
    if urls:
        process_videos(urls)
        print(f"Processed {len(urls)} videos successfully. Check ../data/finished_vids/ for output files.")
    else:
        print("No URLs provided. Exiting.")
