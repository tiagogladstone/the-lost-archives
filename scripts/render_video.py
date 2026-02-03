
import os
import argparse
import subprocess
import tempfile
import shutil
import itertools
import json

# --- Ken Burns Effect Function (copied from apply_ken_burns.py) ---

def get_video_dimensions(video_path):
    """Gets the width and height of a video."""
    cmd = [
        "ffprobe",
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height",
        "-of", "json",
        video_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        # Fallback for images that ffprobe treats differently
        cmd_img = ["ffprobe", "-v", "error", "-show_entries", "stream=width,height", "-of", "json", video_path]
        result_img = subprocess.run(cmd_img, capture_output=True, text=True)
        if result_img.returncode != 0:
            raise RuntimeError(f"ffprobe failed for {video_path}: {result.stderr} {result_img.stderr}")
        data = json.loads(result_img.stdout)
    else:
        data = json.loads(result.stdout)
    
    if not data["streams"]:
        raise RuntimeError(f"Could not get dimensions for {video_path}")
        
    return data["streams"][0]["width"], data["streams"][0]["height"]


def apply_ken_burns(input_media, output_video, duration=5, effect="zoom_in", fps=25, resolution="1920x1080"):
    """
    Applies Ken Burns effect to an image or video.
    """
    # For simplicity, we'll use a fixed resolution for the zoompan canvas
    w, h = map(int, resolution.split('x'))

    total_frames = int(duration * fps)

    # These expressions are complex, carefully crafted for FFmpeg
    vf_options = {
        "zoom_in": f"zoompan=z='min(zoom+0.0015,1.5)':d={total_frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={w}x{h}",
        "zoom_out": f"zoompan=z='if(lte(zoom,1.0),1.5,max(1.001,zoom-0.0015))':d={total_frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={w}x{h}",
        "pan_left": f"zoompan=z=1.2:d=1:x='iw/2-(iw/zoom/2)-(iw*t)/(2*({duration}))':y='ih/2-(ih/zoom/2)':s={w}x{h}",
        "pan_right": f"zoompan=z=1.2:d=1:x='iw/2-(iw/zoom/2)+(iw*t)/(2*({duration}))':y='ih/2-(ih/zoom/2)':s={w}x{h}",
    }

    vf = vf_options.get(effect)
    if not vf:
        raise ValueError(f"Invalid effect: {effect}")

    command = [
        "ffmpeg",
        "-y",
        "-i", input_media,
        "-vf", f"scale={w}:-1,crop={w}:{h},{vf}", # Scale, crop to 16:9, then apply effect
        "-c:v", "libx264",
        "-t", str(duration),
        "-pix_fmt", "yuv420p",
        "-preset", "veryfast",
        "-crf", "22",
        output_video
    ]
    
    print(f"Applying Ken Burns ({effect}, {duration:.2f}s) to {os.path.basename(input_media)}...")
    subprocess.run(command, check=True, capture_output=True, text=True)

# --- Original Rendering Logic (Modified) ---

def get_media_duration(media_path):
    """Gets the duration of a media file using ffprobe."""
    command = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        media_path
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        return float(result.stdout.strip())
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"Error getting duration for {media_path}: {e}")
        return 0
    except ValueError:
        print(f"Could not parse duration from ffprobe output for {media_path}")
        return 0

def render_video(clips_dir, narration_path, music_path, output_path, resolution="1920x1080"):
    """
    Renders a video by applying Ken Burns, concatenating clips, and adding audio.
    """
    if not os.path.exists(clips_dir) or not os.listdir(clips_dir):
        print(f"Error: Clips directory '{clips_dir}' is empty or does not exist.")
        return

    if not os.path.exists(narration_path):
        print(f"Error: Narration file not found at '{narration_path}'.")
        return

    video_clips = sorted([os.path.join(clips_dir, f) for f in os.listdir(clips_dir) if f.lower().endswith(('.mp4', '.mov', '.jpg', '.jpeg', '.png'))])
    
    if not video_clips:
        print(f"No media clips found in '{clips_dir}'.")
        return

    narration_duration = get_media_duration(narration_path)
    if narration_duration == 0:
        print("Could not determine narration duration. Aborting render.")
        return
        
    print(f"Total narration duration: {narration_duration:.2f} seconds")
    
    # Calculate duration per clip
    clip_duration = narration_duration / len(video_clips)
    print(f"Calculated duration per clip: {clip_duration:.2f} seconds")

    # Create a temporary directory for processed clips
    processed_clips_dir = tempfile.mkdtemp()
    processed_clips = []

    # Define Ken Burns effects and create a cycle iterator
    effects = ["zoom_in", "pan_right", "zoom_out", "pan_left"]
    effect_cycle = itertools.cycle(effects)

    try:
        # Apply Ken Burns effect to each clip
        for i, clip_path in enumerate(video_clips):
            effect = next(effect_cycle)
            output_clip_path = os.path.join(processed_clips_dir, f"clip_{i:03d}.mp4")
            
            try:
                apply_ken_burns(clip_path, output_clip_path, duration=clip_duration, effect=effect, resolution=resolution)
                processed_clips.append(output_clip_path)
            except (subprocess.CalledProcessError, RuntimeError) as e:
                print(f"Skipping clip {clip_path} due to error during Ken Burns effect: {e}")
                print(f"FFMPEG stderr: {e.stderr if hasattr(e, 'stderr') else 'N/A'}")


        if not processed_clips:
            print("No clips were successfully processed. Aborting render.")
            return

        # Create a temporary file list for ffmpeg with processed clips
        list_file_path = os.path.join(processed_clips_dir, "file_list.txt")
        with open(list_file_path, "w") as f:
            for clip in processed_clips:
                f.write(f"file '{os.path.abspath(clip)}'\n")

        # Build the final ffmpeg command
        ffmpeg_command = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0", "-i", list_file_path,
            "-i", narration_path,
        ]

        filter_complex_parts = []
        # No need to scale video here as Ken Burns function handles it
        filter_complex_parts.append(f"[0:v]setsar=1[v]")

        if os.path.exists(music_path):
            ffmpeg_command.extend(["-i", music_path])
            filter_complex_parts.append(f"[2:a]volume=0.15,afade=t=in:ss=0:d=2[a_bgm]")
            filter_complex_parts.append(f"[1:a]volume=1.0[a_narration]")
            filter_complex_parts.append(f"[a_narration][a_bgm]amix=inputs=2:duration=first[a_out]")
            map_audio = "[a_out]"
        else:
            print("Warning: Background music file not found. Rendering with narration only.")
            filter_complex_parts.append(f"[1:a]volume=1.0[a_out]")
            map_audio = "[a_out]"

        ffmpeg_command.extend([
            "-filter_complex", ";".join(filter_complex_parts),
            "-map", "[v]",
            "-map", map_audio,
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
            "-c:a", "aac", "-b:a", "192k",
            "-t", str(narration_duration),
            output_path
        ])

        print("\nStarting final video rendering process...")
        print("FFmpeg command:", " ".join(ffmpeg_command))
        subprocess.run(ffmpeg_command, check=True)
        print(f"\nVideo rendered successfully to {output_path}")

    except subprocess.CalledProcessError as e:
        print(f"Error during ffmpeg execution: {e}")
    except FileNotFoundError:
        print("Error: ffmpeg is not installed or not in the system's PATH.")
    finally:
        # Clean up the temporary directory for processed clips
        if os.path.exists(processed_clips_dir):
            shutil.rmtree(processed_clips_dir)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Render a video using FFmpeg with Ken Burns effects.")
    parser.add_argument("--clips_dir", type=str, required=True, help="Directory containing video/image clips.")
    parser.add_argument("--narration", type=str, required=True, help="Path to the narration audio file.")
    parser.add_argument("--music", type=str, required=False, default="", help="Path to the background music file (optional).")
    parser.add_argument("--output", type=str, required=True, help="Path to save the final video.")
    parser.add_argument("--resolution", type=str, default="1920x1080", help="Output video resolution (e.g., 1920x1080).")
    
    args = parser.parse_args()
    
    render_video(args.clips_dir, args.narration, args.music, args.output, args.resolution)
