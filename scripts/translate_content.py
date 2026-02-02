
import os
import argparse
import google.generativeai as genai
from dotenv import load_dotenv

def translate_content(input_path, target_language, output_path):
    """
    Translates text from an input file to a target language using the Gemini API.

    Args:
        input_path (str): The path to the input file.
        target_language (str): The target language for translation.
        output_path (str): The path to save the translated content.
    """
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found in environment variables.")

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')

    try:
        with open(input_path, "r", encoding="utf-8") as f:
            content_to_translate = f.read()

        prompt = f"Translate the following text to {target_language}:\n\n{content_to_translate}"
        
        print(f"Translating content from {input_path} to {target_language}...")
        response = model.generate_content(prompt)
        
        if response.text:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(response.text)
            print(f"Translated content saved successfully to {output_path}")
        else:
            print("Error: Received an empty response from the API.")

    except FileNotFoundError:
        print(f"Error: Input file not found at {input_path}")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Translate text using the Gemini API.")
    parser.add_argument("--input", type=str, required=True, help="The path to the input file.")
    parser.add_argument("--target", type=str, required=True, help="The target language for translation.")
    parser.add_argument("--output", type=str, required=True, help="The path to save the translated content.")
    
    args = parser.parse_args()
    
    translate_content(args.input, args.target, args.output)
