from elevenlabs.client import ElevenLabs
import elevenlabs

client = ElevenLabs(
        api_key="19383af207ac93a828db987d90c51056"
)

def getTextAudio(filename, text):
    text_audio = client.generate(
        text = text,
        voice = "Adam"
    )
    elevenlabs.save(text_audio, f"../data/text_audio/{filename}.mp3")
    return f"../data/text_audio/{filename}.mp3"
