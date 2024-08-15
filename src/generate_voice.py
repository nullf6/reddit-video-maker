from elevenlabs.client import ElevenLabs
import elevenlabs

client = ElevenLabs(
        api_key="1c2c4ff62affa70dcd3aef0f5bf63d9e"
)

def getTextAudio(filename, text):
    text_audio = client.generate(
        text = text,
        voice = "Adam"
    )
    elevenlabs.save(text_audio, f"../data/text_audio/{filename}.mp3")
    return f"../data/text_audio/{filename}.mp3"
