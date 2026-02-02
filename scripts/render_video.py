
import os
import argparse
import subprocess

def get_video_duration(video_path):
    """Gets the duration of a video file using ffprobe."""
    command = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        video_path
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        return float(result.stdout.strip())
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"Error getting duration for {video_path}: {e}")
        return 0
    except ValueError:
        print(f"Could not parse duration from ffprobe output for {video_path}")
        return 0

def render_video(clips_dir, narration_path, music_path, output_path, resolution="1920x1080"):
    """
    Renders a video by concatenating clips, adding narration and background music.

    Args:
        clips_dir (str): Directory containing the video clips.
        narration_path (str): Path to the narration audio file.
        music_path (str): Path to the background music file.
        output_path (str): Path to save the final rendered video.
        resolution (str): The output video resolution (e.g., "1920x1080").
    """
    if not os.path.exists(clips_dir) or not os.listdir(clips_dir):
        print(f"Error: Clips directory '{clips_dir}' is empty or does not exist.")
        return

    if not os.path.exists(narration_path):
        print(f"Error: Narration file not found at '{narration_path}'.")
        return

    video_clips = sorted([os.path.join(clips_dir, f) for f in os.listdir(clips_dir) if f.endswith(('.mp4', '.mov'))])
    
    if not video_clips:
        print(f"No video clips found in '{clips_dir}'.")
        return

    # Create a temporary file list for ffmpeg
    list_file_path = os.path.join(clips_dir, "file_list.txt")
    with open(list_file_path, "w") as f:
        for clip in video_clips:
            f.write(f"file '{os.path.abspath(clip)}'\n")

    # Get the total duration of the narration to match the video length
    narration_duration = get_video_duration(narration_path)
    if narration_duration == 0:
        print("Could not determine narration duration. Aborting render.")
        return
        
    print(f"Narration duration: {narration_duration:.2f} seconds")

    # Build the ffmpeg command
    # -i narration: input narration
    # -i music: input music
    # -filter_complex: defines audio processing
    #   [1:a]...[a_bgm]: process background music (music input)
    #   [0:a]...[a_narration]: process narration (narration input)
    #   [a_narration][a_bgm]amix=...: mix the two audio streams
    # -c:v copy: copy video stream without re-encoding (faster)
    # -c:a aac: use AAC audio codec
    # -shortest: finish encoding when the shortest input stream ends (the concatenated video)
    
    ffmpeg_command = [
        "ffmpeg",
        "-y",  # Overwrite output file if it exists
        "-f", "concat",
        "-safe", "0",
        "-i", list_file_path,  # Input from the file list
        "-i", narration_path, # Input for narration
    ]

    filter_complex_parts = []
    # Video processing: scale all clips to the target resolution
    filter_complex_parts.append(f"[0:v]scale={resolution},setsar=1[v]")

    if os.path.exists(music_path):
        ffmpeg_command.extend(["-i", music_path]) # Input for background music
        # Audio processing with background music
        # Set music volume to 15%, fade in for the first 2 seconds
        # Mix narration (at full volume) with background music
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
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "22",
        "-c:a", "aac",
        "-b:a", "192k",
        "-t", str(narration_duration), # Set total duration to match narration
        output_path
    ])

    try:
        print("\nStarting video rendering process...")
        print("FFmpeg command:", " ".join(ffmpeg_command))
        subprocess.run(ffmpeg_command, check=True)
        print(f"\nVideo rendered successfully to {output_path}")

    except subprocess.CalledProcessError as e:
        print(f"Error during ffmpeg execution: {e}")
    except FileNotFoundError:
        print("Error: ffmpeg is not installed or not in the system's PATH.")
    finally:
        # Clean up the temporary file list
        if os.path.exists(list_file_path):
            os.remove(list_file_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Render a video using FFmpeg.")
    parser.add_argument("--clips_dir", type=str, required=True, help="Directory containing video clips.")
    parser.add_argument("--narration", type=str, required=True, help="Path to the narration audio file.")
    parser.add_argument("--music", type=str, required=False, default="", help="Path to the background music file (optional).")
    parser.add_argument("--output", type=str, required=True, help="Path to save the final video.")
    parser.add_argument("--resolution", type=str, default="1920x1080", help="Output video resolution (e.g., 1920x1080).")
    
    args = parser.parse_args()
    
    render_video(args.clips_dir, args.narration, args.music, args.output, args.resolution)
