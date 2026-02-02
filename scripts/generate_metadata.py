
import os
import argparse
import json
import google.generativeai as genai
from dotenv import load_dotenv

def generate_metadata(topic, languages, output_path):
    """
    Generates titles (3 variations), description, and tags for a video in multiple languages.

    Args:
        topic (str): The topic of the video.
        languages (list): A list of language codes (e.g., ['en', 'pt-br']).
        output_path (str): The path to save the generated metadata as a JSON file.
    """
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found in environment variables.")

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')

    metadata = {}

    for lang in languages:
        print(f"Generating metadata for {topic} in {lang}...")
        
        prompt = f"""
        Generate video metadata for the topic '{topic}' in the language '{lang}'.
        I need the following in a JSON format:
        - 'titles': A list of 3 creative and engaging titles.
        - 'description': A concise and informative description.
        - 'tags': A list of relevant keywords/tags.
        
        Return only the JSON object.
        """
        
        try:
            response = model.generate_content(prompt)
            # Clean up the response to ensure it's valid JSON
            clean_response = response.text.strip().replace("```json", "").replace("```", "").strip()
            
            if clean_response:
                metadata[lang] = json.loads(clean_response)
                print(f"Successfully generated metadata for {lang}.")
            else:
                print(f"Warning: Received an empty response for {lang}.")
                metadata[lang] = {}

        except json.JSONDecodeError:
            print(f"Error: Failed to decode JSON for language {lang}. Response was: {clean_response}")
            metadata[lang] = {"error": "Failed to decode JSON", "response": clean_response}
        except Exception as e:
            print(f"An error occurred while generating metadata for {lang}: {e}")
            metadata[lang] = {"error": str(e)}

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=4, ensure_ascii=False)
        
    print(f"\nMetadata generation complete. Saved to {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate video metadata in multiple languages.")
    parser.add_argument("--topic", type=str, required=True, help="The topic of the video.")
    parser.add_argument("--languages", nargs='+', required=True, help="List of languages (e.g., en pt-br es).")
    parser.add_argument("--output", type=str, required=True, help="The path to save the metadata JSON file.")
    
    args = parser.parse_args()
    
    generate_metadata(args.topic, args.languages, args.output)
