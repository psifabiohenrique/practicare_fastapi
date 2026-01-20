import logging
import math
import os
import subprocess

logger = logging.getLogger(__name__)


def get_audio_duration(file_path: str) -> float:
    """Gets the duration of an audio file in seconds using ffprobe."""
    try:
        cmd = [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            file_path,
        ]
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
        )
        return float(result.stdout.strip())
    except Exception as e:
        logger.error(f"Error getting audio duration: {e}")
        raise


def split_audio(
    file_path: str, output_dir: str, max_size_mb: int = 20
) -> list[str]:
    """
    Splits an audio file into chunks of approximately max_size_mb.
    Returns a list of paths to the generated chunks.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
    if file_size_mb <= max_size_mb:
        return [file_path]

    duration = get_audio_duration(file_path)

    # Estimate number of chunks based on size
    num_chunks = math.ceil(file_size_mb / max_size_mb)
    chunk_duration = duration / num_chunks

    chunks = []
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    extension = os.path.splitext(file_path)[1]

    for i in range(num_chunks):
        start_time = i * chunk_duration
        output_path = os.path.join(
            output_dir, f"{base_name}_part{i}{extension}"
        )

        cmd = [
            "ffmpeg",
            "-i",
            file_path,
            "-ss",
            str(start_time),
            "-t",
            str(chunk_duration),
            "-c",
            "copy",
            "-y",
            output_path,
        ]

        try:
            subprocess.run(
                cmd,
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
            )
            chunks.append(output_path)
        except subprocess.CalledProcessError as e:
            logger.error(
                f"FFmpeg splitting failed at part {i}: {e.stderr.decode()}"
            )
            raise

    return chunks
