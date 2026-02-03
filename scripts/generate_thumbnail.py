
import argparse
import os
import requests
from PIL import Image, ImageDraw, ImageFont
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
    
def add_text_to_image(image, text):
    """Adds text to the image with a subtle background for readability."""
    draw = ImageDraw.Draw(image)

    # Try to find a common bold font, fallback to default
    font_path = "/System/Library/Fonts/Supplemental/Arial Bold.ttf" # macOS common
    if not os.path.exists(font_path):
        font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" # Linux common
    
    try:
        # Dynamically adjust font size
        font_size = 120
        font = ImageFont.truetype(font_path, font_size)
        
        # Adjust font size based on text length to fit the width
        while draw.textlength(text, font=font) > image.width - 100:
            font_size -= 5
            font = ImageFont.truetype(font_path, font_size)

    except IOError:
        print("Default bold font not found. Using default PIL font.")
        font = ImageFont.load_default()

    # Calculate text position to center it
    text_width = draw.textlength(text, font=font)
    text_height = font.size
    
    x = (image.width - text_width) / 2
    y = (image.height - text_height) / 2 + 100 # Position it lower on the screen

    # Add a subtle stroke for better readability
    stroke_width = 3
    stroke_fill = "black"
    draw.text((x-stroke_width, y-stroke_width), text, font=font, fill=stroke_fill)
    draw.text((x+stroke_width, y-stroke_width), text, font=font, fill=stroke_fill)
    draw.text((x-stroke_width, y+stroke_width), text, font=font, fill=stroke_fill)
    draw.text((x+stroke_width, y+stroke_width), text, font=font, fill=stroke_fill)

    # Add main text
    draw.text((x, y), text, font=font, fill="white")
    
    return image

def generate_thumbnail(topic, title, output_path):
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


    print(f"Adding title: {title}")
    final_image = add_text_to_image(image, title.upper())

    # Create output directory if it doesn't exist
    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)

    print(f"Saving thumbnail to: {output_path}")
    final_image.save(output_path, "PNG")
    print("Thumbnail generated successfully!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate a YouTube thumbnail.")
    parser.add_argument("--topic", required=True, help="The topic to search for an image (e.g., 'The Mystery of the Nazca Lines')")
    parser.add_argument("--title", required=True, help="The catchy title to display on the thumbnail (e.g., 'ANCIENT ALIENS?')")
    parser.add_argument("--output", required=True, help="The output path for the PNG image (e.g., 'output/thumbnail.png')")

    args = parser.parse_args()

    # It's a good practice to pass the API key via environment variables
    # For this script, we'll use the one hardcoded if the env var is not set.
    if not PEXELS_API_KEY:
        print("Error: PEXELS_API_KEY environment variable not set.")
    else:
        generate_thumbnail(args.topic, args.title, args.output)
