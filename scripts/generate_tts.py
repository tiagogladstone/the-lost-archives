
import os
import argparse
import requests
import yaml
import base64

def load_voices_config():
    """Loads the voice configuration from the YAML file."""
    # Assuming the script is in 'scripts/' and the config is in 'config/'
    # relative to the project root.
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_path = os.path.join(project_root, 'config', 'voices.yaml')
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        print(f"Error: Voice configuration file not found at {config_path}")
        return None
    except yaml.YAMLError as e:
        print(f"Error parsing YAML file: {e}")
        return None

def chunk_text(text, chunk_size=4500):
    """Splits text into chunks of a specified size."""
    return [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]

def generate_tts(input_path, output_path, language):
    """
    Generates audio from a text file using Google Cloud TTS API.

    Args:
        input_path (str): The path to the input text file.
        output_path (str): The path to save the generated audio file (e.g., narration.mp3).
        language (str): The language identifier (e.g., 'pt-BR', 'en-US').
    """
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY not found in environment variables.")

    voices_config = load_voices_config()
    if not voices_config or language not in voices_config:
        raise ValueError(f"Language '{language}' not found in voices configuration.")

    voice_info = voices_config[language]
    voice_name = voice_info['voice_name']
    language_code = voice_info['language_code']

    tts_url = f"https://texttospeech.googleapis.com/v1/text:synthesize?key={api_key}"

    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            text = f.read()

        if not text.strip():
            print("Warning: Input file is empty.")
            return

        text_chunks = chunk_text(text)
        audio_chunks = []

        print(f"Generating audio from {input_path} for language '{language}'...")
        for i, chunk in enumerate(text_chunks):
            print(f"Processing chunk {i+1}/{len(text_chunks)}...")
            
            payload = {
                'input': {'text': chunk},
                'voice': {'languageCode': language_code, 'name': voice_name, 'ssmlGender': 'MALE'},
                'audioConfig': {'audioEncoding': 'MP3'}
            }
            
            response = requests.post(tts_url, json=payload)
            response.raise_for_status() 
            
            response_json = response.json()
            audio_content = response_json.get('audioContent')
            if audio_content:
                audio_chunks.append(base64.b64decode(audio_content))
            else:
                print(f"Warning: No audio content received for chunk {i+1}. Response: {response_json}")

        if audio_chunks:
            # Ensure the output directory exists
            output_dir = os.path.dirname(output_path)
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)
            
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
        if e.response:
            print(f"Response status: {e.response.status_code}")
            print(f"Response content: {e.response.text}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Generate TTS audio from a text file using Google Cloud.')
    parser.add_argument('--input', type=str, required=True, help='Path to the input text file.')
    parser.add_argument('--output', type=str, required=True, help='Path to save the output MP3 file.')
    parser.add_argument('--language', type=str, required=True, choices=['pt-BR', 'en-US', 'es-ES'], help='The language for TTS.')
    
    args = parser.parse_args()
    
    # PyYAML is required. Check if installed.
    try:
        import yaml
    except ImportError:
        print("Error: PyYAML is not installed. Please install it using: pip install PyYAML")
        exit(1)

    generate_tts(args.input, args.output, args.language)
