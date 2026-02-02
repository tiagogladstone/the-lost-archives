
import os
import argparse
import subprocess
import yaml

def generate_tts_for_languages(base_input_path, base_output_path, languages, voices_config_path):
    """
    Wrapper script to generate TTS audio for multiple languages.
    
    It assumes input files are named like 'script_en.txt', 'script_pt-br.txt'.
    Output files will be named 'narration_en.mp3', 'narration_pt-br.mp3'.

    Args:
        base_input_path (str): The base path for input scripts (e.g., 'artifacts/scripts/script').
        base_output_path (str): The base path for output audio (e.g., 'artifacts/audio/narration').
        languages (list): A list of language codes to process.
        voices_config_path (str): Path to the voices.yaml config file.
    """
    try:
        with open(voices_config_path, 'r') as f:
            voices_config = yaml.safe_load(f)
    except FileNotFoundError:
        print(f"Error: Voices config file not found at {voices_config_path}")
        return
    except yaml.YAMLError as e:
        print(f"Error parsing YAML file: {e}")
        return

    print("Starting TTS generation for multiple languages...")
    
    for lang in languages:
        input_file = f"{base_input_path}_{lang}.txt"
        output_file = f"{base_output_path}_{lang}.mp3"
        
        if not os.path.exists(input_file):
            print(f"Warning: Input file {input_file} not found. Skipping language '{lang}'.")
            continue
            
        voice_info = voices_config.get(lang)
        if not voice_info:
            print(f"Warning: No voice configuration found for language '{lang}' in {voices_config_path}. Skipping.")
            continue

        voice_name = voice_info.get('voice_name')
        language_code = voice_info.get('language_code')

        if not voice_name or not language_code:
            print(f"Warning: Incomplete voice configuration for language '{lang}'. Skipping.")
            continue

        print(f"\n--- Generating for language: {lang} ---")
        print(f"Input: {input_file}")
        print(f"Output: {output_file}")
        print(f"Voice: {voice_name}, Language Code: {language_code}")

        try:
            command = [
                "python",
                "scripts/generate_tts.py",
                "--input", input_file,
                "--output", output_file,
                "--voice", voice_name,
                "--language", language_code
            ]
            
            # Ensure the script is called from the project root
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            subprocess.run(command, check=True, cwd=project_root, capture_output=True, text=True)
            print(f"Successfully generated TTS for {lang}.")

        except subprocess.CalledProcessError as e:
            print(f"Error generating TTS for {lang}:")
            print(f"Return code: {e.returncode}")
            print(f"Output: {e.stdout}")
            print(f"Error Output: {e.stderr}")
        except Exception as e:
            print(f"An unexpected error occurred for {lang}: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate TTS audio for multiple languages.")
    parser.add_argument("--input_base", type=str, required=True, help="Base path for input text files (e.g., artifacts/script).")
    parser.add_argument("--output_base", type=str, required=True, help="Base path for output audio files (e.g., artifacts/narration).")
    parser.add_argument("--languages", nargs='+', required=True, help="List of languages to process (e.g., en pt-br).")
    parser.add_argument("--config", type=str, default="config/voices.yaml", help="Path to the voices configuration file.")
    
    args = parser.parse_args()
    
    # The script assumes it's being run from the root of the project.
    # We pass the relative path to the generate_tts.py script.
    generate_tts_for_languages(args.input_base, args.output_base, args.languages, args.config)
