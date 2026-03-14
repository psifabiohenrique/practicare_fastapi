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


def split_by_vad(wav_path: str, output_dir: str) -> str:
    vad = webrtcvad.Vad(1)

    os.makedirs(output_dir, exist_ok=True)

    input_name = os.path.splitext(os.path.basename(wav_path))[0]
    output_path = os.path.join(output_dir, f"{input_name}_vad.wav")

    with wave.open(wav_path, "rb") as wf:
        rate = wf.getframerate()
        sample_width = wf.getsampwidth()
        n_channels = wf.getnchannels()

        if sample_width != 2:  # noqa: PLR2004
            raise ValueError("Audio must be 16-bit PCM (sample_width=2)")

        frame_samples = int(rate * FRAME_MS / 1000)
        frame_size_bytes = frame_samples * sample_width

        silence_count = 0
        wrote_any_speech = False

        # Arquivo de saída é aberto uma única vez
        with save_segment(
            output_path,
            rate,
            n_channels,
            sample_width,
        ) as out_wf:
            while True:
                frame = wf.readframes(frame_samples)
                if len(frame) < frame_size_bytes:
                    break

                is_speech = vad.is_speech(frame, rate)

                if is_speech:
                    silence_count = 0
                    out_wf.writeframes(frame)
                    wrote_any_speech = True
                else:
                    silence_count += 1
                    silence_count = min(
                        silence_count,
                        SILENCE_THRESHOLD_FRAMES,
                    )

    # Se nenhum trecho de fala foi detectado,
    # você pode optar por remover o arquivo
    if not wrote_any_speech:
        os.remove(output_path)
        raise ValueError("No speech detected in audio.")

    return output_path


def save_segment(
    path: str,
    rate: int,
    n_channels: int,
    sample_width: int,
):
    wf = wave.open(path, "wb")
    wf.setnchannels(n_channels)
    wf.setsampwidth(sample_width)
    wf.setframerate(rate)
    return wf
