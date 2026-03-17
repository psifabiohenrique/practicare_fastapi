import math
import os
import struct
import subprocess
import wave
from unittest.mock import patch

import pytest

from src.utils.audio_processor import (
    convert_to_wav,
    get_audio_duration,
    split_audio,
    split_by_vad,
)


@pytest.fixture
def temp_audio_dir(tmp_path):
    d = tmp_path / "audio"
    d.mkdir()
    return str(d)


def create_wav_file(
    path,
    duration_seconds=1.0,
    sample_rate=16000,
    frequency=440.0,
    silence=False,
):
    """Creates a 16-bit mono WAV file."""
    num_samples = int(duration_seconds * sample_rate)
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(sample_rate)

        if silence:
            samples = [0] * num_samples
        else:
            # Generate a sine wave
            samples = [
                int(
                    32767 * math.sin(2 * math.pi * frequency * i / sample_rate)
                )
                for i in range(num_samples)
            ]

        # Pack into binary
        data = struct.pack("<" + "h" * len(samples), *samples)
        wf.writeframes(data)
    return path


class TestAudioProcessor:
    def test_get_audio_duration(self, temp_audio_dir):
        path = os.path.join(temp_audio_dir, "test.wav")
        create_wav_file(path, duration_seconds=1.5)

        duration = get_audio_duration(path)
        assert math.isclose(duration, 1.5, rel_tol=0.1)

    def test_get_audio_duration_error(self):
        with pytest.raises(Exception, match=""):  # noqa: PT011
            get_audio_duration("non_existent.wav")

    def test_convert_to_wav(self, temp_audio_dir):
        input_path = os.path.join(temp_audio_dir, "input.wav")
        create_wav_file(input_path, duration_seconds=0.5)
        output_path = os.path.join(temp_audio_dir, "output.wav")

        result = convert_to_wav(input_path, output_path)
        assert result == output_path
        assert os.path.exists(output_path)

        # Check if it is a valid wav with correct params
        with wave.open(output_path, "rb") as wf:
            assert wf.getframerate() == 16000
            assert wf.getnchannels() == 1
            assert wf.getsampwidth() == 2

    def test_split_audio_no_split_needed(self, temp_audio_dir):
        path = os.path.join(temp_audio_dir, "small.wav")
        create_wav_file(path, duration_seconds=1.0)

        # File is small, should return same path
        chunks = split_audio(path, temp_audio_dir, max_size_mb=10)
        assert chunks == [path]

    def test_split_audio_with_splitting(self, temp_audio_dir):
        path = os.path.join(temp_audio_dir, "to_split.wav")
        create_wav_file(path, duration_seconds=2.0)

        # Mock getsize to simulate a large file
        # 2 MB file, max_size 1 MB -> should split into 2 chunks
        with patch("os.path.getsize", return_value=2 * 1024 * 1024):
            chunks = split_audio(path, temp_audio_dir, max_size_mb=1)

        assert len(chunks) == 2
        for chunk in chunks:
            assert os.path.exists(chunk)
            assert chunk.endswith(".wav")

    def test_split_audio_creates_output_dir(self, tmp_path):
        # Test line 46: os.makedirs(output_dir)
        new_dir = str(tmp_path / "new_non_existent_dir")
        path = os.path.join(str(tmp_path), "creates_dir.wav")
        create_wav_file(path)

        chunks = split_audio(path, new_dir, max_size_mb=10)
        assert os.path.exists(new_dir)
        assert chunks == [path]

    def test_split_audio_with_splitting_error(self, temp_audio_dir):
        # Test lines 90-94: subprocess.CalledProcessError
        path = os.path.join(temp_audio_dir, "to_split_error.wav")
        create_wav_file(path, duration_seconds=2.0)

        # Mock getsize to simulate a large file
        # And mock subprocess to fail ONLY when ffmpeg is called for splitting
        original_run = subprocess.run

        def side_effect(cmd, *args, **kwargs):
            if "ffmpeg" in cmd and "-ss" in cmd:
                raise subprocess.CalledProcessError(
                    1, cmd, stderr=b"FFmpeg failed"
                )
            return original_run(cmd, *args, **kwargs)

        with patch("os.path.getsize", return_value=2 * 1024 * 1024):
            with patch("subprocess.run", side_effect=side_effect):
                with pytest.raises(subprocess.CalledProcessError):
                    split_audio(path, temp_audio_dir, max_size_mb=1)

    def test_split_by_vad_success(self, temp_audio_dir):
        # Create a wav with 0.5s speech, 0.5s silence, 0.5s speech
        path = os.path.join(temp_audio_dir, "vad_input.wav")

        sample_rate = 16000
        speech_samples = [
            int(32767 * math.sin(2 * math.pi * 440 * i / sample_rate))
            for i in range(int(0.5 * sample_rate))
        ]
        silence_samples = [0] * int(0.5 * sample_rate)
        all_samples = speech_samples + silence_samples + speech_samples

        with wave.open(path, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            data = struct.pack("<" + "h" * len(all_samples), *all_samples)
            wf.writeframes(data)

        output_path = split_by_vad(path, temp_audio_dir)
        assert os.path.exists(output_path)
        assert "_vad.wav" in output_path

        # Duration should be less than 1.5s because silence was removed
        duration = get_audio_duration(output_path)
        assert duration < 1.5

    def test_split_by_vad_no_speech(self, temp_audio_dir):
        path = os.path.join(temp_audio_dir, "silence.wav")
        create_wav_file(path, duration_seconds=1.0, silence=True)

        with pytest.raises(ValueError, match="No speech detected in audio"):
            split_by_vad(path, temp_audio_dir)

    def test_split_by_vad_invalid_width(self, temp_audio_dir):
        path = os.path.join(temp_audio_dir, "invalid_width.wav")
        # Create 8-bit wav (sample width 1)
        with wave.open(path, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(1)
            wf.setframerate(16000)
            wf.writeframes(b"\x00" * 1600)

        with pytest.raises(ValueError, match="Audio must be 16-bit PCM"):
            split_by_vad(path, temp_audio_dir)
