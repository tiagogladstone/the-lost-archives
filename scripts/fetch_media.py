
import os
import argparse
import requests
import google.generativeai as genai
from dotenv import load_dotenv

def extract_keywords(script_path, num_keywords=10):
    """
    Extracts keywords from a script file using Gemini API.

    Args:
        script_path (str): The path to the script file.
        num_keywords (int): The number of keywords to extract.

    Returns:
        list: A list of keywords.
    """
    print(f"Extracting keywords from {script_path}...")
    try:
        with open(script_path, 'r', encoding='utf-8') as f:
            script_text = f.read()

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables.")

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        prompt = f"Extract the {num_keywords} most relevant keywords for stock video footage from the following script. Return them as a comma-separated list:\n\n{script_text}"
        
        response = model.generate_content(prompt)
        
        if response.text:
            keywords = [kw.strip() for kw in response.text.split(',')]
            print(f"Extracted keywords: {keywords}")
            return keywords
        else:
            print("Warning: Could not extract keywords, using topic as a fallback.")
            return []
            
    except FileNotFoundError:
        print(f"Error: Script file not found at {script_path}")
        return []
    except Exception as e:
        print(f"An error occurred during keyword extraction: {e}")
        return []


def search_and_download_videos(keywords, output_dir, per_page=5):
    """
    Searches for videos on Pexels API and downloads them.

    Args:
        keywords (list): A list of keywords to search for.
        output_dir (str): The directory to save the downloaded videos.
        per_page (int): The number of videos to download per keyword.
    """
    load_dotenv()
    pexels_api_key = os.getenv("PEXELS_API_KEY")
    if not pexels_api_key:
        raise ValueError("PEXELS_API_KEY not found in environment variables.")

    headers = {"Authorization": pexels_api_key}
    search_url = "https://api.pexels.com/videos/search"
    
    os.makedirs(output_dir, exist_ok=True)
    downloaded_count = 0

    for keyword in keywords:
        print(f"\nSearching for videos with keyword: '{keyword}'...")
        params = {"query": keyword, "per_page": per_page, "orientation": "landscape"}
        
        try:
            response = requests.get(search_url, headers=headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            videos = data.get("videos", [])
            
            if not videos:
                print(f"No videos found for '{keyword}'.")
                continue

            for video in videos:
                video_files = video.get("video_files", [])
                # Find a suitable HD resolution
                download_url = next((f['link'] for f in video_files if 1280 < f['width'] < 2000 and f.get('quality') == 'hd'), None)
                
                if not download_url:
                    # Fallback to the first available link if no ideal one is found
                    download_url = video_files[0]['link'] if video_files else None

                if download_url:
                    try:
                        video_response = requests.get(download_url, stream=True)
                        video_response.raise_for_status()
                        
                        file_name = f"{keyword.replace(' ', '_')}_{video['id']}.mp4"
                        file_path = os.path.join(output_dir, file_name)
                        
                        print(f"Downloading {file_name}...")
                        with open(file_path, "wb") as f:
                            for chunk in video_response.iter_content(chunk_size=8192):
                                f.write(chunk)
                        downloaded_count += 1
                        
                    except requests.exceptions.RequestException as e:
                        print(f"Error downloading video {video['id']}: {e}")
                        
        except requests.exceptions.RequestException as e:
            print(f"Error searching for videos with keyword '{keyword}': {e}")

    print(f"\nDownload complete. Total videos downloaded: {downloaded_count}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch video clips from Pexels based on a script.")
    parser.add_argument("--script", type=str, required=True, help="Path to the video script file.")
    parser.add_argument("--output_dir", type=str, required=True, help="Directory to save the downloaded videos.")
    parser.add_argument("--num_keywords", type=int, default=10, help="Number of keywords to extract from the script.")
    parser.add_argument("--videos_per_keyword", type=int, default=3, help="Number of videos to download per keyword.")
    
    args = parser.parse_args()
    
    keywords = extract_keywords(args.script, args.num_keywords)
    
    if not keywords:
        # Fallback to using the script's filename as a topic if keyword extraction fails
        topic_fallback = os.path.basename(args.script).split('.')[0].replace('_', ' ')
        print(f"Using fallback topic: '{topic_fallback}'")
        keywords = [topic_fallback]

    if keywords:
        search_and_download_videos(keywords, args.output_dir, args.videos_per_keyword)
    else:
        print("Could not proceed without keywords.")
