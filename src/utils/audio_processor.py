import logging
import math
import os
import subprocess
import wave

import webrtcvad

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


def convert_to_wav(input_path: str, output_path: str) -> str:
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            input_path,
            "-ac",
            "1",
            "-ar",
            "16000",
            "-f",
            "wav",
            output_path,
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return output_path


FRAME_MS = 30
SILENCE_THRESHOLD_FRAMES = 10  # ~300ms
MAX_CHUNK_BYTES = 20 * 1024 * 1024  # 20 MB


def split_by_vad(wav_path: str, output_dir: str) -> list[str]:

    vad = webrtcvad.Vad(3)

    os.makedirs(output_dir, exist_ok=True)

    with wave.open(wav_path, "rb") as wf:
        segments_paths = []
        rate = wf.getframerate()
        sample_width = wf.getsampwidth()  # deve ser 2
        file_name = os.path.splitext(os.path.basename(wav_path))[0]

        frame_size = int(rate * FRAME_MS / 1000) * sample_width

        current_frames = []
        current_bytes = 0
        silence_count = 0
        segment_index = 0

        while True:
            frame = wf.readframes(frame_size // sample_width)
            if len(frame) < frame_size:
                break

            is_speech = vad.is_speech(frame, rate)

            if is_speech:
                current_frames.append(frame)
                current_bytes += len(frame)
                silence_count = 0
            else:
                silence_count += 1
                silence_count = min(silence_count, SILENCE_THRESHOLD_FRAMES)

        #     reached_size_limit = current_bytes >= MAX_CHUNK_BYTES
        #     # reached_silence_limit = silence_count >= SILENCE_THRESHOLD_FRAMES  # noqa: E501

        #     if reached_size_limit and current_frames:
        #         segment_name = f"{file_name}_segment_{segment_index}"
        #         segments_paths.append(
        #             save_segment(
        #                 current_frames,
        #                 output_dir,
        #                 segment_name,
        #                 rate,
        #             )
        #         )

        #         segment_index += 1
        #         current_frames = []
        #         current_bytes = 0
        #         silence_count = 0

        # flush final
        if current_frames:
            segment_name = f"{file_name}_segment_{segment_index}"
            segments_paths = save_segment(
                current_frames,
                output_dir,
                segment_name,
                rate,
            )
    return segments_paths


def save_segment(frames, output_dir, file_name, rate) -> str:
    path = f"{output_dir}/segment_{file_name}.wav"
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        wf.writeframes(b"".join(frames))
    return path
