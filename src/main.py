import fetch_data
import generate_voice
import create_box
from moviepy.editor import VideoFileClip, CompositeVideoClip, TextClip, AudioFileClip, ImageClip, concatenate_videoclips,concatenate_audioclips, afx, CompositeAudioClip
import random

background_video = "../data/background_video.mp4"
url = input("Enter the url of the post: ")
music_choice = {
    1: "../data/background_music/undertale.m4a",
    2: "../data/background_music/remix.m4a",
    3: "../data/background_music/undertale_shop.m4a",
    4: "../data/background_music/solitude.m4a",
    5: "../data/background_music/israel.m4a"
}

try:
    choice = int(input("Choose your music. \n1. Undertale \n2. Remix \n3. Undertale Shop \n4. M83 - Solitude \n5. Israel\nEnter your input: "))
    bgmusic = music_choice.get(choice, "Invalid option, please select a valid option")
except ValueError:
    print("Invalid input. Please enter a number.")

post_title = fetch_data.getSubmissionTitle(url)
post_body = fetch_data.getSubmissionBody(url)

title_audio = generate_voice.getTextAudio('title', post_title)
body_audio = generate_voice.getTextAudio('body', post_title)

post_image = create_box.create_text_image_with_overlay(post_title, 20, '../data/logo.png', 'lol.png')
