import os
import re
import random
from pathlib import Path

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
from moviepy.video.fx.all import crop

import whisper_timestamped as whisper
from audiostretchy.stretch import stretch_audio
from PIL import Image, ImageDraw

import fetch_data
import create_box
from tiktokvoice import tts

# ---------- Config ----------
os.environ["FFMPEG_BINARY"] = "/usr/bin/ffmpeg"

FONT = "Montserrat-ExtraBold"
FONT_SIZE = 90
SHADOW_STROKE = 10
BACKGROUND_MUSIC_VOL = 0.15
FPS = 60

DATA_DIR = Path("../data")
TEXT_AUDIO_DIR = DATA_DIR / "text_audio"
FINISHED_DIR = DATA_DIR / "finished_vids"
BACKGROUND_VIDEO_PATH = DATA_DIR / "background_video.webm"
BACKGROUND_MUSIC_PATH = DATA_DIR / "background_music" / "up_theme.mp3"
LOGO_PATH = DATA_DIR / "logo.png"

TEXT_AUDIO_DIR.mkdir(parents=True, exist_ok=True)
FINISHED_DIR.mkdir(parents=True, exist_ok=True)


def change_voice_pacing(voice_path: Path, speed: float = 0.85) -> Path:
    new_path = voice_path.with_name(f"{voice_path.stem}_speed{speed}{voice_path.suffix}")
    stretch_audio(str(voice_path), str(new_path), speed)
    return new_path


def create_masked_overlay(image_path: Path, output_path: Path, corner_radius: int = 20, new_size=None) -> None:
    """Round corners with alpha mask. Optional resizing."""
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
    """
    Creates bouncing subtitle clips from whisper_timestamped output.
    """
    text_clips = []

    def bounce(t):
        # quick pop at the beginning of each word
        return 1.1 + 0.1 * (1 - (t / 0.1) ** 2) if t <= 0.1 else 1.0

    for segment in transcribed_text.get("segments", []):
        words = segment.get("words", [])
        i = 0
        while i < len(words):
            word_group = words[i:i + 2] if random.random() < 0.3 else words[i:i + 1]
            text = " ".join(word["text"] for word in word_group).strip()

            start_time = float(word_group[0]["start"])
            end_time = float(word_group[-1]["end"])

            shadow_clip = (
                TextClip(
                    text,
                    font=FONT,
                    fontsize=FONT_SIZE,
                    color="black",
                    stroke_color="black",
                    stroke_width=SHADOW_STROKE,
                )
                .set_start(start_time)
                .set_end(end_time)
                .resize(lambda t: bounce(t))
                .set_position("center")
            )

            text_clip = (
                TextClip(text, font=FONT, fontsize=FONT_SIZE, color="white")
                .set_start(start_time)
                .set_end(end_time)
                .resize(lambda t: bounce(t))
                .set_position("center")
            )

            # Composite subtitle layers
            text_clips.append(CompositeVideoClip([shadow_clip, text_clip]).set_position("center"))
            i += len(word_group)

    return text_clips


def parse_text(text: str) -> str:
    """Parses and replaces abbreviations and age-gender formats."""
    replacements = {
        r"\bAITA\b": "Am I the Asshole?",
        r"\bTIFU\b": "Today I Fucked Up",
        r"\bpussy\b": "coochie",
        r"\bF(\d{2})\b": r"Female \1",
        r"\bM(\d{2})\b": r"Male \1",
        r"\b(\d{2})F\b": r"Female \1",
        r"\b(\d{2})M\b": r"Male \1",
        r"\((\d{2})F\)": r"(Female \1)",
        r"\((\d{2})M\)": r"(Male \1)",
        r"\(F(\d{2})\)": r"(Female \1)",
        r"\(M(\d{2})\)": r"(Male \1)",
    }
    for pattern, repl in replacements.items():
        text = re.sub(pattern, repl, text)
    return text


def censor_text(text: str) -> str:
    """Censors specific words."""
    censored_words = {
        r"\bfuck\b": "f*ck",
        r"\bshit\b": "sh*t",
        r"\basshole\b": "a**hole",
        r"\bbitch\b": "b*tch",
        r"\bcondom\b": "c*ndom",
        r"\bpussy\b": "p*ssy",
        r"\bdamn\b": "d*mn",
        r"\bhell\b": "h*ll",
    }
    for pattern, repl in censored_words.items():
        text = re.sub(pattern, repl, text, flags=re.IGNORECASE)
    return text


def _fit_background_to_duration(background_video: VideoFileClip, total_duration: float) -> VideoFileClip:
    """
    Ensures the background can provide total_duration.
    If too short, loop it. If long enough, take a random subclip.
    """
    if background_video.duration <= 0:
        raise ValueError("Background video has invalid duration.")

    if background_video.duration >= total_duration + 0.1:
        start_time = random.uniform(0, background_video.duration - total_duration)
        return background_video.subclip(start_time, start_time + total_duration)

    # Loop to fill
    loops = int(total_duration // background_video.duration) + 1
    clips = [background_video] * loops
    looped = concatenate_videoclips(clips)
    return looped.subclip(0, total_duration)


def create_tiktok_clip(
    model,
    background_video_path: Path,
    background_music_path: Path,
    voice1_path: Path,
    voice2_path: Path,
    overlay_image_path: Path,
    output_path: Path,
    overlay_size=None,
    animation_rate: float = 0.4,
):
    background_video = VideoFileClip(str(background_video_path))
    background_music = AudioFileClip(str(background_music_path))
    voice1 = AudioFileClip(str(voice1_path))
    voice2 = AudioFileClip(str(voice2_path))

    # Transcribe voice2 once
    transcribed_text = whisper.transcribe(model, str(voice2_path), language="en")

    total_duration = float(voice1.duration + voice2.duration + 2.0)

    # Fit background to duration (loop or random subclip)
    background_video = _fit_background_to_duration(background_video, total_duration)

    # Crop to 9:16
    background_video = crop(
        background_video,
        width=background_video.h * 9 / 16,
        height=background_video.h,
        x_center=background_video.w / 2,
    )

    # Masked overlay unique per output to avoid overwriting
    masked_overlay_path = output_path.with_suffix("").with_name(output_path.stem + "_masked_overlay.png")
    create_masked_overlay(overlay_image_path, masked_overlay_path, new_size=overlay_size)

    overlay_image = ImageClip(str(masked_overlay_path)).set_duration(voice1.duration)
    overlay_image = overlay_image.resize(lambda t: 0.95 + 0.05 * min(1, t / animation_rate)).set_position("center")

    intro_background = background_video.subclip(0, voice1.duration)
    intro_clip = CompositeVideoClip([intro_background, overlay_image]).set_audio(voice1)

    text_clips = get_text_clips(transcribed_text)

    main_background = background_video.subclip(voice1.duration, total_duration)
    main_clip = CompositeVideoClip([main_background] + text_clips).set_audio(voice2)

    final_clip = concatenate_videoclips([intro_clip, main_clip])

    background_music = afx.audio_loop(background_music, duration=total_duration)
    final_audio = CompositeAudioClip([background_music.volumex(BACKGROUND_MUSIC_VOL), final_clip.audio])

    # Small trim to avoid encoder trailing issues
    final_audio = final_audio.subclip(0, max(0.0, final_audio.duration - 0.5))
    finished_clip = final_clip.set_audio(final_audio)

    finished_clip.write_videofile(str(output_path), codec="libx264", fps=FPS)

    # Optional: cleanup masked overlay file
    try:
        masked_overlay_path.unlink(missing_ok=True)
    except Exception:
        pass


def process_videos(urls):
    # Load Whisper model once
    model = whisper.load_model("medium", device="cpu")

    for url in urls:
        try:
            submission_id = fetch_data.getSubmissionID(url)
            post_title_raw = fetch_data.getSubmissionTitle(url)
            post_body_raw = fetch_data.getSubmissionBody(url)

            safe_title = censor_text(post_title_raw)
            overlay_img_path_str = create_box.create_text_image_with_overlay(
                safe_title, 20, str(LOGO_PATH), "lol.png"
            )

            # Some versions return just a path; normalize
            overlay_img_path = Path(overlay_img_path_str) if isinstance(overlay_img_path_str, str) else Path(overlay_img_path_str[0])

            post_title = parse_text(post_title_raw)
            post_body = parse_text(post_body_raw)

            voice1_path = TEXT_AUDIO_DIR / f"postVoice_{submission_id}.mp3"
            voice2_path = TEXT_AUDIO_DIR / f"bodyVoice_{submission_id}.mp3"

            v1 = Path(tts(post_title, "en_us_010", str(voice1_path)))
            v2 = Path(tts(post_body, "en_us_010", str(voice2_path)))
            v2 = change_voice_pacing(v2, speed=0.85)

            # If overlay size is needed, read dimensions
            # Default: scale to a reasonable width
            overlay_size = (950, 350) if not overlay_img_path.exists() else None

            output_path = FINISHED_DIR / f"{submission_id}_video.mp4"

            create_tiktok_clip(
                model=model,
                background_video_path=BACKGROUND_VIDEO_PATH,
                background_music_path=BACKGROUND_MUSIC_PATH,
                voice1_path=v1,
                voice2_path=v2,
                overlay_image_path=overlay_img_path,
                output_path=output_path,
                overlay_size=overlay_size,
                animation_rate=0.1,
            )

            print(f"[OK] Created: {output_path}")

        except Exception as e:
            print(f"[ERROR] Failed for URL {url}: {e}")


def input_urls():
    urls = []
    while True:
        url = input("Enter a Reddit post URL (or 'done' to finish): ").strip()
        if url.lower() == "done":
            break
        if url.startswith("https://www.reddit.com"):
            urls.append(url)
        else:
            print("Invalid URL. Please enter a valid Reddit post URL.")
    return urls


if __name__ == "__main__":
    print("Welcome to the TikTok video generator!")
    urls = input_urls()
    if urls:
        process_videos(urls)
        print(f"Processed {len(urls)} videos. Check {FINISHED_DIR}/ for output files.")
    else:
        print("No URLs provided. Exiting.")
