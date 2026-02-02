import os
import argparse
from google import genai

def generate_script(topic, language, output_path):
    """
    Generates a video script using the Gemini API.
    """
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY not found in environment variables.")

    client = genai.Client(api_key=api_key)

    prompt = f"""Create a detailed YouTube video script about "{topic}" in {language}.

Requirements:
- Duration: 8-10 minutes when narrated
- Start with a hook that grabs attention in the first 10 seconds
- Include surprising facts and little-known information
- Use a narrative, storytelling style
- End with a thought-provoking conclusion
- Only output the narration text, no stage directions or timestamps

Topic: {topic}
Language: {language}
"""

    try:
        print(f"Generating script for topic: {topic} in {language}...")
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=prompt
        )
        
        if response.text:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(response.text)
            print(f"Script saved successfully to {output_path}")
            print(f"Length: {len(response.text)} characters")
        else:
            print("Error: Received an empty response from the API.")

    except Exception as e:
        print(f"An error occurred: {e}")
        raise

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate a video script using the Gemini API.")
    parser.add_argument("--topic", type=str, required=True, help="The topic of the video.")
    parser.add_argument("--language", type=str, required=True, help="The language of the script.")
    parser.add_argument("--output", type=str, required=True, help="The path to save the generated script.")
    
    args = parser.parse_args()
    
    generate_script(args.topic, args.language, args.output)
