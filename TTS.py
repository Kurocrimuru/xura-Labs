import os
import torch
import requests
import urllib.parse
from pydub import AudioSegment
from pydub.playback import play

def silero_tts(tts, language='en', model='v3_en', speaker='en_21'):
    device = torch.device('cpu')
    torch.set_num_threads(4)
    local_file = 'model.pt'

    if not os.path.isfile(local_file):
        torch.hub.download_url_to_file(f'https://models.silero.ai/models/tts/{language}/{model}.pt', local_file)

    model = torch.package.PackageImporter(local_file).load_pickle("tts_models", "model")
    model.to(device)

    sample_rate = 48000

    audio_path = model.save_wav(text=tts, speaker=speaker, sample_rate=sample_rate)
    return audio_path

def voicevox_tts(tts):
    # You need to run VoicevoxEngine.exe first before running this script
    voicevox_url = 'http://localhost:50021'

    params_encoded = urllib.parse.urlencode({'text': tts, 'speaker': 47})
    request = requests.post(f'{voicevox_url}/audio_query?{params_encoded}')
    params_encoded = urllib.parse.urlencode({'speaker': 47, 'enable_interrogative_upspeak': True})
    request = requests.post(f'{voicevox_url}/synthesis?{params_encoded}', json=request.json())

    output_file = "voicevox_output.wav"
    with open(output_file, "wb") as outfile:
        outfile.write(request.content)
    return output_file

def play_audio(file_path):
    audio = AudioSegment.from_wav(file_path)
    play(audio)

if __name__ == "__main__":
    text = "こんにちは、私の名前はユナです、助けてください、クロさん"

    # Uncomment the TTS engine you want to use

    # Silero TTS
    # audio_file = silero_tts(text)

    # Voicevox TTS
    audio_file = voicevox_tts(text)

    # Play the audio
    play_audio(audio_file)




