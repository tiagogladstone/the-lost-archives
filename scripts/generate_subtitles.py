
import argparse
import re
from datetime import timedelta

def format_time(seconds):
    """Converts seconds to SRT time format (HH:MM:SS,ms)."""
    delta = timedelta(seconds=seconds)
    hours, remainder = divmod(delta.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    milliseconds = int(delta.microseconds / 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"

def generate_subtitles(input_file, output_file, words_per_minute):
    """
    Generates an SRT subtitle file from a text script.
    """
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            script_text = f.read()
    except FileNotFoundError:
        print(f"Error: Input file not found at {input_file}")
        return

    # Split script into sentences or short phrases.
    # This regex splits by '.', '!', '?', or newline characters, keeping the delimiter.
    segments = re.split(r'(?<=[.!?])\s+|\n', script_text)
    segments = [seg.strip() for seg in segments if seg.strip()]

    if not segments:
        print("Warning: No text segments found in the input file.")
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("") # Create an empty file
        return

    wps = words_per_minute / 60.0  # words per second
    current_time = 0.0
    subtitle_index = 1

    with open(output_file, 'w', encoding='utf-8') as f:
        for segment in segments:
            word_count = len(segment.split())
            if word_count == 0:
                continue

            duration = word_count / wps
            start_time = current_time
            end_time = start_time + duration

            f.write(f"{subtitle_index}\n")
            f.write(f"{format_time(start_time)} --> {format_time(end_time)}\n")
            f.write(f"{segment}\n\n")

            current_time = end_time
            subtitle_index += 1

    print(f"Successfully generated subtitles at {output_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate SRT subtitles from a text script.")
    parser.add_argument("--input", required=True, help="Path to the input text script file.")
    parser.add_argument("--output", required=True, help="Path to the output .srt file.")
    parser.add_argument("--words-per-minute", type=int, default=150, help="Estimated words per minute for narration speed.")

    args = parser.parse_args()

    generate_subtitles(args.input, args.output, args.words_per_minute)
