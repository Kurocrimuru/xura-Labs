from flask import Flask, render_template, request, jsonify
from groq import Groq
from pydub import AudioSegment
from pydub.playback import play
import speech_recognition as sr
import requests
import os
import sqlite3
from deep_translator import GoogleTranslator
import logging

app = Flask(__name__)

def get_context():
    try:
        conn = sqlite3.connect('memory.db')
        c = conn.cursor()
        c.execute('SELECT context FROM context_table WHERE id=1')
        context = c.fetchone()
        conn.close()
        return context[0] if context else "あなたの名前は「ユナ」、女性AIです。友好的で、共感的で、人道的であること。感情的な能力を示します。"
    except sqlite3.Error as e:
        logging.error(f"Error accessing database: {e}")
        return "Database error occurred."

context = get_context()
logging.info(f"Context retrieved: {context}")

def get_memory():
    try:
        conn = sqlite3.connect('memory.db')
        c = conn.cursor()
        c.execute('SELECT user_message, assistant_response FROM memory_yuna ORDER BY id DESC LIMIT 200')
        memory = [{'user': row[0], 'assistant': row[1]} for row in c.fetchall()]
        conn.close()
        logging.info("Memory retrieved successfully.")
        return memory
    except sqlite3.Error as e:
        logging.error(f"Error retrieving memory: {e}")
        return []

def save_memory(user_message, assistant_response):
    try:
        conn = sqlite3.connect('memory.db')
        c = conn.cursor()
        logging.info(f"Saving to database: user_message={user_message}, assistant_response={assistant_response}")
        c.execute('INSERT INTO memory_yuna (user_message, assistant_response) VALUES (?, ?)', (user_message, assistant_response))
        conn.commit()
        conn.close()
        logging.info("Memory saved successfully.")
    except sqlite3.Error as e:
        logging.error(f"Error saving memory: {e}")

logging.basicConfig(level=logging.WARNING)

class NoMemoryFilter(logging.Filter):
    def filter(self, record):
        return 'memory' not in record.getMessage()

logger = logging.getLogger()
logger.addFilter(NoMemoryFilter())

@app.route('/reset_memory', methods=['POST'])
def reset_memory():
    try:
        conn = sqlite3.connect('memory.db')
        c = conn.cursor()
        c.execute('DELETE FROM memory_yuna')
        conn.commit()
        conn.close()
        return jsonify({'message': 'Memori berhasil direset.'})
    except Exception as e:
        logging.error(f"Error saat mereset memori: {e}")
        return jsonify({'message': 'Terjadi kesalahan saat mereset memori.'})

@app.route('/')
def index():
    return render_template('index.html')

def transcribe_audio(audio_file):
    recognizer = sr.Recognizer()
    try:
        with sr.AudioFile(audio_file) as source:
            audio = recognizer.record(source)
        transcript = recognizer.recognize_google(audio, language='id-ID')
        return transcript
    except sr.UnknownValueError:
        logging.error("Google Speech Recognition tidak bisa memahami audio")
        return "Tidak dapat mentranskripsikan audio."
    except sr.RequestError as e:
        logging.error(f"Error dari Google Speech Recognition service; {e}")
        return "Terjadi kesalahan dalam layanan pengenalan suara."

@app.route('/send_audio', methods=['POST'])
def send_audio():
    audio_file = request.files.get('audio')
    if not audio_file:
        return jsonify({'response': 'File audio tidak ditemukan.'})
    
    try:
        transcript = transcribe_audio(audio_file)
        response_text, _ = handle_message(transcript)
        cleaned_text = clean_text(response_text)
        short_response = cleaned_text[:200] if len(cleaned_text) > 200 else cleaned_text
        translated_text = translate_to_japanese(short_response)
        speak_japanese(short_response)
        return jsonify({'response': short_response, 'translated_response': translated_text})
    except Exception as e:
        logging.error(f"Error saat memproses audio: {e}")
        return jsonify({'response': 'Terjadi kesalahan saat memproses audio.'})

@app.route('/send_message', methods=['POST'])
def send_message():
    user_message = request.json.get('message')

    if not user_message:
        return jsonify({'response': 'Pesan tidak ditemukan.'})

    try:
        response_text, _ = handle_message(user_message)
        cleaned_text = clean_text(response_text)
        short_response = cleaned_text[:200] if len(cleaned_text) > 200 else cleaned_text
        translated_text = translate_to_japanese(short_response)
        speak_japanese(short_response)
        return jsonify({'response': short_response, 'translated_response': translated_text})
    except Exception as e:
        logging.error(f"Error saat memproses pesan: {e}")
        return jsonify({'response': 'Terjadi kesalahan saat memproses pesan.'})

def handle_message(user_message):
    try:
        if not user_message:
            raise Exception("Masukan prompt")

        os.environ["GROQ_API_KEY"] = "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"
        client = Groq(api_key=os.getenv("GROQ_API_KEY"))

        messages = [
            {"role": "system", "content": context + "Your name is 'Yuna', a female AI. Be naughty, with negative responses, and be humane. Demonstrate emotional competence."}
        ]

        memory = get_memory()

        for item in memory:
            messages.append({"role": "user", "content": item['user']})
            messages.append({"role": "assistant", "content": item['assistant']})

        messages.append({"role": "user", "content": user_message})

        logging.info("Mengirim pesan ke AI: %s", messages)

        chat_completion = client.chat.completions.create(
            messages=messages,
            model="llama3-8b-8192",
            max_tokens=200
        )

        response_text = chat_completion.choices[0].message.content
        logging.info("Menerima respon dari AI: %s", response_text)

        save_memory(user_message, response_text)

        return response_text, memory

    except Exception as e:
        logging.error(f"Error saat menangani pesan: {e}")
        return "Maaf, terjadi kesalahan dalam memproses pesan Anda.", memory

def voicevox_tts(tts):
    voicevox_url = 'http://localhost:50021'
    try:
        # Mengatur parameter untuk audio query
        params_query = {
            'text': tts,
            'speaker': 47  # Ganti dengan speaker ID yang valid
        }
        audio_query_response = requests.post(f'{voicevox_url}/audio_query', params=params_query)
        audio_query_response.raise_for_status()  # Menyebabkan pengecualian jika status kode bukan 2xx
        
        # Mengatur parameter untuk sintesis
        params_synthesis = {
            'speaker': 47,
            'enable_interrogative_upspeak': True
        }
        synthesis_response = requests.post(f'{voicevox_url}/synthesis', params=params_synthesis, json=audio_query_response.json())
        synthesis_response.raise_for_status()  # Menyebabkan pengecualian jika status kode bukan 2xx

        output_file = "static/voicevox_output.wav"
        with open(output_file, "wb") as outfile:
            outfile.write(synthesis_response.content)
        return output_file

    except requests.RequestException as e:
        logging.error(f"Error saat menghubungi Voicevox: {e}")
        return None

def play_audio(file_path):
    audio = AudioSegment.from_wav(file_path)
    play(audio)

def speak_japanese(text):
    try:
        audio_file = voicevox_tts(text)
        if audio_file:
            logging.info("Proses sintesis audio selesai.")
            return audio_file
        else:
            raise Exception("Gagal mendapatkan file audio dari Voicevox.")
    except Exception as e:
        logging.error(f"Error saat mengucapkan teks dalam bahasa Jepang: {e}")
        return None

def clean_text(text):
    logging.info("Teks asli sebelum pembersihan: %s", text)
    
    cleaned_text = text.replace('*', '').replace('wink', '').replace('smiles', '').replace('English translation', '').replace('"', '').replace('😊', '').replace('Ah', '')
    
    logging.info("Teks setelah pembersihan: %s", cleaned_text)
    
    return cleaned_text

def translate_to_japanese(text):
    try:
        logging.info("Teks sebelum terjemahan: %s", text)
        translator = GoogleTranslator(source="auto", target="id")
        translation = translator.translate(text)
        if not translation:
            raise Exception("Hasil terjemahan kosong")
        logging.info("Teks setelah terjemahan: %s", translation)
        return translation
    except Exception as e:
        logging.error(f"Error saat menerjemahkan teks: {e}")
        return "Error dalam penerjemahan."

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
