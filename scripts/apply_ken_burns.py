#!/usr/bin/env python3
"""Apply Ken Burns effect (zoom/pan) to static images using FFmpeg."""

import subprocess
import argparse
import os
import json

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
        raise RuntimeError(f"ffprobe failed: {result.stderr}")
    
    data = json.loads(result.stdout)
    return data["streams"][0]["width"], data["streams"][0]["height"]


def apply_ken_burns(input_image, output_video, duration=5, effect="zoom_in", fps=25):
    """
    Aplica efeito Ken Burns em uma imagem.
    
    Effects:
    - zoom_in: Começa afastado, termina próximo
    - zoom_out: Começa próximo, termina afastado
    - pan_left: Move da direita para esquerda
    - pan_right: Move da esquerda para direita
    """

    img_w, img_h = get_video_dimensions(input_image)

    # Calculate the total number of frames
    total_frames = duration * fps

    vf_options = {
        "zoom_in": f"zoompan=z='min(zoom+0.001,1.5)':d={total_frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={img_w}x{img_h}",
        "zoom_out": f"zoompan=z='if(lte(zoom,1.0),1.5,max(1.001,zoom-0.001))':d={total_frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={img_w}x{img_h}",
        "pan_left": f"zoompan=z=1.2:d={total_frames}:x='if(gte(x,0),x-iw/200,0)':y='ih/2-(ih/zoom/2)':s={img_w}x{img_h}",
        "pan_right": f"zoompan=z=1.2:d={total_frames}:x='if(lte(x,iw),x+iw/200,iw)':y='ih/2-(ih/zoom/2)':s={img_w}x{img_h}"
    }

    vf = vf_options.get(effect)
    if not vf:
        raise ValueError(f"Invalid effect: {effect}")

    command = [
        "ffmpeg",
        "-y",
        "-loop", "1",
        "-i", input_image,
        "-vf", vf,
        "-c:v", "libx264",
        "-t", str(duration),
        "-pix_fmt", "yuv420p",
        output_video
    ]

    print(f"Executing command: {' '.join(command)}")
    subprocess.run(command, check=True)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--duration', type=int, default=5)
    parser.add_argument('--effect', default='zoom_in', choices=['zoom_in', 'zoom_out', 'pan_left', 'pan_right'])
    args = parser.parse_args()
    apply_ken_burns(args.input, args.output, args.duration, args.effect)
