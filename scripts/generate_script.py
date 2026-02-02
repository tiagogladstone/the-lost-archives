
import os
import argparse
import google.generativeai as genai
from dotenv import load_dotenv

def generate_script(topic, language, output_path):
    """
    Generates a video script using the Gemini API.

    Args:
        topic (str): The topic of the video.
        language (str): The language of the script.
        output_path (str): The path to save the generated script.
    """
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found in environment variables.")

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')

    prompt = f"Create a detailed video script about {topic} in {language}. The script should be engaging and informative."

    try:
        print(f"Generating script for topic: {topic} in {language}...")
        response = model.generate_content(prompt)
        
        if response.text:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(response.text)
            print(f"Script saved successfully to {output_path}")
        else:
            print("Error: Received an empty response from the API.")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate a video script using the Gemini API.")
    parser.add_argument("--topic", type=str, required=True, help="The topic of the video.")
    parser.add_argument("--language", type=str, required=True, help="The language of the script.")
    parser.add_argument("--output", type=str, required=True, help="The path to save the generated script.")
    
    args = parser.parse_args()
    
    generate_script(args.topic, args.language, args.output)
