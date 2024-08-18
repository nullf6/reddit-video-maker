from elevenlabs.client import ElevenLabs
import elevenlabs

client = ElevenLabs(
        api_key="b7adedff883eac0b0f72cb53bce2091c"
)

def getTextAudio(filename, text):
    text_audio = client.generate(
        text = text,
        voice = "Adam"
    )
    elevenlabs.save(text_audio, f"../data/text_audio/{filename}.mp3")
    return f"../data/text_audio/{filename}.mp3"
