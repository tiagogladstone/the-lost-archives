
import os
import argparse
import json
from google import genai

def generate_metadata(topic, languages, output_path):
    """
    Generates titles (3 variations), description, and tags for a video in multiple languages.

    Args:
        topic (str): The topic of the video.
        languages (list): A list of language codes (e.g., ['pt-BR']).
        output_path (str): The path to save the generated metadata as a JSON file.
    """
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY not found in environment variables.")

    client = genai.Client(api_key=api_key)
    model = client.models.get('gemini-1.5-flash') # Using 1.5 flash as it's good for this kind of task

    metadata = {}

    for lang in languages:
        print(f"Generating metadata for '{topic}' in {lang}...")
        
        prompt = f"""
        You are a YouTube content strategist. Your task is to generate compelling metadata for a video about the topic: "{topic}".
        The target language for the metadata is: {lang}.

        Please generate the following, formatted as a single, valid JSON object, and nothing else.

        1.  **titles**: An object containing exactly three variations of the title:
            -   `curiosity_driven`: A title that sparks curiosity and asks a question (e.g., "What if...?").
            -   `direct`: A straightforward, keyword-rich title for SEO.
            -   `provocative`: A bold or controversial title that challenges the viewer's assumptions.

        2.  **description**: A concise, SEO-friendly description of about 150-200 words. It should start with a strong hook, naturally include keywords related to the topic, and end with a call to action (e.g., "Subscribe for more stories like this!").

        3.  **tags**: A list of exactly 15 relevant and specific tags, including a mix of broad and long-tail keywords.

        Example for "The Fall of Rome":
        {{
          "titles": {{
            "curiosity_driven": "What If Rome Never Fell? The World We Never Knew",
            "direct": "The History of the Roman Empire's Collapse",
            "provocative": "Why Rome Deserved to Fall"
          }},
          "description": "...",
          "tags": ["ancient rome", "fall of rome", "roman empire", ...]
        }}

        Now, generate the JSON for the topic "{topic}" in {lang}. Output ONLY the JSON object.
        """
        
        try:
            # Forcing JSON output
            response = model.generate_content(
                contents=prompt,
                generation_config={"response_mime_type": "application/json"}
            )
            
            # The response text should now be a clean JSON string
            clean_response = response.text.strip()
            
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

    # Ensure the output directory exists
    if output_path:
        output_dir = os.path.dirname(output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=4, ensure_ascii=False)
            
        print(f"\\nMetadata generation complete. Saved to {output_path}")
    else:
        # If no output path, print to stdout
        print(json.dumps(metadata, indent=4, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate video metadata using the Google GenAI API.")
    parser.add_argument("--topic", type=str, required=True, help="The topic of the video.")
    parser.add_argument("--languages", type=str, required=True, help="Comma-separated list of language codes (e.g., pt-BR,en,es).")
    parser.add_argument("--output", type=str, required=True, help="The path to save the metadata JSON file.")
    
    args = parser.parse_args()
    
    # Split the languages string into a list
    languages_list = [lang.strip() for lang in args.languages.split(',')]
    
    generate_metadata(args.topic, languages_list, args.output)
