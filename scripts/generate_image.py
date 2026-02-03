#!/usr/bin/env python3
"""Generate images using the Google Genai API."""

import os
import argparse
import google.genai as genai
from google.genai.types import GenerateImagesConfig

def generate_image(prompt, output_path, style="photorealistic"):
    """
    Generates an image using the Google Genai API.
    
    Args:
        prompt: The description of the image.
        output_path: The path to save the generated image.
        style: The style of the image (e.g., photorealistic, artistic).
    """
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("The GOOGLE_API_KEY environment variable is not set.")

    try:
        client = genai.Client(api_key=api_key)

        enhanced_prompt = f"{prompt}, {style} style"
        print(f"Generating image with prompt: '{enhanced_prompt}'")

        # This is the client-based API call
        response = client.models.generate_images(
            model="imagen-4.0-generate-001",  # Using the specific Imagen 4 model
            prompt=enhanced_prompt,
            config=GenerateImagesConfig(
                number_of_images=1,
                aspect_ratio="16:9",
                output_mime_type="image/png",
            ),
        )

        if response.generated_images:
            # The response object has a `save` method for the image
            response.generated_images[0].image.save(output_path)
            print(f"Image saved successfully to {output_path}")
        else:
            print("Image generation failed. No images were returned.")
            # Check for other information in the response if needed
            print(f"Full response: {response}")


    except Exception as e:
        print(f"An error occurred during image generation: {e}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Generate images using the Google Genai API.")
    parser.add_argument('--prompt', required=True, help="Description of the image to generate.")
    parser.add_argument('--output', required=True, help="Path to save the output image.")
    parser.add_argument('--style', default='photorealistic', help="Style of the image (e.g., photorealistic, artistic).")
    args = parser.parse_args()
    
    generate_image(args.prompt, args.output, args.style)
