
import argparse
import os
import requests
from PIL import Image, ImageDraw
import io

# It's better to load the API key from an environment variable for security
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "xZ9dO5TIsHvPxsfURdidfT5BMSbvFfgPF7gQZeDIR2cTOeSA8mSRzOM1")
PEXELS_API_URL = "https://api.pexels.com/v1/search"
TARGET_WIDTH = 1280
TARGET_HEIGHT = 720

def search_image(query):
    """Searches for an image on Pexels and returns the URL of the first result."""
    headers = {"Authorization": PEXELS_API_KEY}
    params = {"query": query, "per_page": 1, "orientation": "landscape"}
    try:
        response = requests.get(PEXELS_API_URL, headers=headers, params=params)
        response.raise_for_status()  # Raise an exception for bad status codes
        data = response.json()
        if data["photos"]:
            return data["photos"][0]["src"]["large2x"]
    except requests.exceptions.RequestException as e:
        print(f"Error fetching image from Pexels: {e}")
    return None

def download_image(url):
    """Downloads an image from a URL and returns it as a PIL Image object."""
    try:
        response = requests.get(url)
        response.raise_for_status()
        return Image.open(io.BytesIO(response.content))
    except requests.exceptions.RequestException as e:
        print(f"Error downloading image: {e}")
    return None

def create_gradient(width, height):
    """Creates a transparent gradient overlay that darkens the bottom of the image."""
    gradient = Image.new("L", (width, height), 0)
    draw = ImageDraw.Draw(gradient)
    for i in range(height):
        # Start the gradient from the middle of the image
        alpha = int(255 * (i / height) * 0.8) # Adjust 0.8 to make it darker or lighter
        draw.line([(0, i), (width, i)], fill=alpha)
    return gradient

def generate_thumbnail(topic, output_path):
    """Main function to generate the thumbnail."""
    print(f"Searching for image with topic: {topic}")
    image_url = search_image(topic)

    if not image_url:
        print("Could not find an image for the given topic.")
        return

    print(f"Downloading image from: {image_url}")
    image = download_image(image_url)

    if not image:
        print("Failed to download the image.")
        return

    # Resize and crop to the exact target dimensions
    image = image.resize((TARGET_WIDTH, TARGET_HEIGHT), Image.Resampling.LANCZOS)
    
    print("Adding dark gradient...")
    gradient = create_gradient(TARGET_WIDTH, TARGET_HEIGHT)
    # Apply gradient as an alpha mask on a black background
    black_bg = Image.new("RGBA", (TARGET_WIDTH, TARGET_HEIGHT), (0, 0, 0, 0))
    # Paste the black layer using the gradient as a mask
    image.paste(black_bg, (0, 0), gradient)

    # Create output directory if it doesn't exist
    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)

    print(f"Saving thumbnail to: {output_path}")
    image.save(output_path, "PNG")
    print("Thumbnail generated successfully!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate a YouTube thumbnail.")
    parser.add_argument("--topic", required=True, help="The topic to search for an image (e.g., 'The Mystery of the Nazca Lines')")
    parser.add_argument("--output", required=True, help="The output path for the PNG image (e.g., 'output/thumbnail.png')")

    args = parser.parse_args()

    # It's a good practice to pass the API key via environment variables
    # For this script, we'll use the one hardcoded if the env var is not set.
    if not PEXELS_API_KEY:
        print("Error: PEXELS_API_KEY environment variable not set.")
    else:
        generate_thumbnail(args.topic, args.output)
