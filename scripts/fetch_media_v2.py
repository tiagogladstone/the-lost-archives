
import os
import argparse
import google.generativeai as genai
from generate_image import generate_image

def extract_image_prompts(script_path, num_prompts=12):
    """
    Extracts detailed image prompts from a script file using Gemini API.

    Args:
        script_path (str): The path to the script file.
        num_prompts (int): The target number of prompts to extract.

    Returns:
        list: A list of image prompts.
    """
    print(f"Extracting image prompts from {script_path}...")
    try:
        with open(script_path, 'r', encoding='utf-8') as f:
            script_text = f.read()

        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            # Use the same key as Imagen
            raise ValueError("GOOGLE_API_KEY not found in environment variables.")

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        prompt = f"""
        Analyze the following video script and generate {num_prompts} detailed, vivid, and photorealistic image prompts that visually represent the key scenes.
        Each prompt should describe a complete scene with a clear subject, action, and setting.
        The prompts should follow a logical sequence according to the script's narrative.
        Return the prompts as a Python-parseable list of strings, like this: ["prompt 1", "prompt 2", "prompt 3"]

        Script:
        ---
        {script_text}
        ---
        """
        
        response = model.generate_content(prompt)
        
        if response.text:
            # Safely evaluate the string representation of the list
            import ast
            prompts = ast.literal_eval(response.text.strip())
            if isinstance(prompts, list):
                print(f"Successfully extracted {len(prompts)} prompts.")
                return prompts
            else:
                raise ValueError("The API did not return a valid list of prompts.")
        else:
            print("Warning: Could not extract image prompts from the script.")
            return []
            
    except FileNotFoundError:
        print(f"Error: Script file not found at {script_path}")
        return []
    except Exception as e:
        print(f"An error occurred during prompt extraction: {e}")
        return []


def generate_images_from_script(script_path, output_dir):
    """
    Generates images based on prompts extracted from a script.

    Args:
        script_path (str): The path to the video script file.
        output_dir (str): The directory to save the generated images.
    """
    prompts = extract_image_prompts(script_path, num_prompts=15)
    
    if not prompts:
        print("No prompts were extracted. Cannot generate images.")
        # Exit with a non-zero code to signal failure to the caller (main.py)
        exit(1)

    os.makedirs(output_dir, exist_ok=True)
    generated_count = 0

    for i, prompt_text in enumerate(prompts):
        try:
            image_filename = f"image_{i+1:02d}.png"
            image_path = os.path.join(output_dir, image_filename)
            
            print(f"--- Generating image {i+1}/{len(prompts)} ---")
            generate_image(prompt_text, image_path, style="cinematic, photorealistic, 4k")
            generated_count += 1
        except Exception as e:
            print(f"Failed to generate image for prompt: '{prompt_text}'. Error: {e}")
            # Decide if one failure should stop the whole process. For now, we continue.
    
    print(f"\nImage generation complete. Total images generated: {generated_count}/{len(prompts)}")
    
    if generated_count == 0:
        print("No images were successfully generated.")
        exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate images for a video based on its script.")
    parser.add_argument("--script", type=str, required=True, help="Path to the video script file.")
    parser.add_argument("--output_dir", type=str, required=True, help="Directory to save the generated images.")
    
    args = parser.parse_args()
    
    # Change the current directory to the script's directory
    # so that `generate_image.py` can be imported correctly.
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)

    generate_images_from_script(args.script, args.output_dir)
