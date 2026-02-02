
import os
import argparse
import requests
from dotenv import load_dotenv

def chunk_text(text, chunk_size=4500):
    """Splits text into chunks of a specified size."""
    return [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]

def generate_tts(input_path, output_path, voice_name='en-US-Wavenet-D', language_code='en-US'):
    """
    Generates audio from a text file using Google Cloud TTS API.

    Args:
        input_path (str): The path to the input text file.
        output_path (str): The path to save the generated audio file (e.g., narration.mp3).
        voice_name (str): The name of the voice to use.
        language_code (str): The language code of the voice.
    """
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY") # Assuming the same key is used for TTS
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found in environment variables.")

    tts_url = f"https://texttospeech.googleapis.com/v1/text:synthesize?key={api_key}"

    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            text = f.read()

        text_chunks = chunk_text(text)
        audio_chunks = []

        print(f"Generating audio from {input_path}...")
        for i, chunk in enumerate(text_chunks):
            print(f"Processing chunk {i+1}/{len(text_chunks)}...")
            
            payload = {
                'input': {'text': chunk},
                'voice': {'languageCode': language_code, 'name': voice_name},
                'audioConfig': {'audioEncoding': 'MP3'}
            }
            
            response = requests.post(tts_url, json=payload)
            response.raise_for_status() # Raise an exception for bad status codes
            
            audio_content = response.json().get('audioContent')
            if audio_content:
                audio_chunks.append(requests.utils.base64.b64decode(audio_content))
            else:
                print(f"Warning: No audio content received for chunk {i+1}.")

        if audio_chunks:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, 'wb') as f:
                for chunk in audio_chunks:
                    f.write(chunk)
            print(f"Audio saved successfully to {output_path}")
        else:
            print("Error: No audio was generated.")

    except FileNotFoundError:
        print(f"Error: Input file not found at {input_path}")
    except requests.exceptions.RequestException as e:
        print(f"An error occurred with the API request: {e}")
        print(f"Response content: {e.response.text if e.response else 'No response'}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Generate TTS audio from a text file.')
    parser.add_argument('--input', type=str, required=True, help='Path to the input text file.')
    parser.add_argument('--output', type=str, required=True, help='Path to save the output MP3 file.')
    parser.add_argument('--voice', type=str, default='en-US-Wavenet-D', help='The voice name to use for TTS.')
    parser.add_argument('--language', type=str, default='en-US', help='The language code to use for TTS.')
    
    args = parser.parse_args()
    
    generate_tts(args.input, args.output, args.voice, args.language)
