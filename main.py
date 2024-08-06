import requests

def voicevox_tts(text, speaker_id=0):
    voicevox_url = 'http://localhost:50021'
    
    # Mengirim permintaan untuk audio query
    response = requests.post(f'{voicevox_url}/audio_query', json={'text': text, 'speaker': speaker_id})
    response.raise_for_status()  # Memastikan tidak ada kesalahan pada permintaan
    
    # Mendapatkan data dari audio query
    audio_query = response.json()
    
    # Mengirim permintaan untuk sintesis audio
    response = requests.post(
        f'{voicevox_url}/synthesis',
        json={
            'speaker': speaker_id,
            'enable_interrogative_upspeak': True
        },
        files={'audio_query': ('audio_query.json', str(audio_query), 'application/json')}
    )
    response.raise_for_status()
    
    # Menyimpan audio ke file
    with open("output.wav", "wb") as outfile:
        outfile.write(response.content)

if __name__ == "__main__":
    voicevox_tts("Hello, how are you?")
