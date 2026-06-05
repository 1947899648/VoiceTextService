"""Apply compatibility patches to wenet for Python 3.14 + PyTorch 2.12.

Fixes:
  1. conv2d.py     — split broken torch.nn.modules.conv imports
  2. processor.py  — replace torchaudio audio loading with soundfile
  3. processor.py  — replace torchaudio resample with librosa
  4. soundfile     — restore missing SoundFileRuntimeError for librosa compatibility
"""

import os


def find_wenet_root():
    import wenet
    return os.path.dirname(wenet.__file__)


def patch_conv2d_imports(wenet_root):
    """Fix: torch.nn.modules.conv no longer exports Union/_pair/Tensor/Optional."""
    target = os.path.join(
        wenet_root, "models", "squeezeformer", "conv2d.py")
    if not os.path.exists(target):
        print(f"  SKIP conv2d.py (not found: {target})")
        return False

    with open(target, "r", encoding="utf-8") as f:
        content = f.read()

    old = ("from torch.nn.modules.conv import "
           "_ConvNd, _size_2_t, Union, _pair, Tensor, Optional")
    new = ("from torch.nn.modules.conv import _ConvNd, _size_2_t\n"
           "from torch.nn.modules.utils import _pair\n"
           "from typing import Union, Optional\n"
           "from torch import Tensor")

    if new in content:
        print("  OK  conv2d.py (already patched)")
        return False

    if old not in content:
        print("  ??? conv2d.py (target line not found, already different)")
        return False

    content = content.replace(old, new)
    with open(target, "w", encoding="utf-8") as f:
        f.write(content)
    print("  FIX conv2d.py")
    return True


def patch_decode_wav(wenet_root):
    """Fix: torchaudio.load() -> soundfile.read(). Server guarantees WAV input."""
    target = os.path.join(wenet_root, "dataset", "processor.py")
    if not os.path.exists(target):
        print(f"  SKIP processor.py (not found: {target})")
        return False

    with open(target, "r", encoding="utf-8") as f:
        content = f.read()

    new_func = '''def decode_wav(sample):
    """ Decode a wav file, convert bytes to waveform tensor.
        Inplace operation. Uses soundfile (input guaranteed WAV by server).

        Args:
            sample: {key, wav, ...}

        Returns:
            {key, wav, sample_rate, ...}
    """
    import soundfile as sf
    assert 'key' in sample
    assert 'wav' in sample
    wav_file = sample['wav']
    if isinstance(wav_file, bytes):
        wav_file = io.BytesIO(wav_file)
    if isinstance(wav_file, io.BytesIO):
        wav_file.seek(0)
    if 'start' in sample:
        assert 'end' in sample
        info = sf.info(wav_file)
        sample_rate = info.samplerate
        start_frame = int(sample['start'] * sample_rate)
        end_frame = int(sample['end'] * sample_rate)
        waveform, _ = sf.read(wav_file, start=start_frame,
                              stop=end_frame, dtype='float32')
    else:
        waveform, sample_rate = sf.read(wav_file, dtype='float32')
    waveform = torch.from_numpy(waveform).unsqueeze(0)
    del sample['wav']
    sample['wav'] = waveform
    sample['sample_rate'] = sample_rate
    return sample'''

    if new_func in content:
        print("  OK  processor.py decode_wav (already patched)")
        return False

    old_torchaudio = '''def decode_wav(sample):
    """ Decode a wav file, convert bytes to waveform tensor.
        Inplace operation.

        Args:
            sample: {key, wav, ...}

        Returns:
            {key, wav, sample_rate, ...}
    """
    assert 'key' in sample
    assert 'wav' in sample
    wav_file = sample['wav']  # str/io.BytesIO, directly load in torchaudio
    if isinstance(wav_file, bytes):
        wav_file = io.BytesIO(wav_file)
    if 'start' in sample:
        assert 'end' in sample
        sample_rate = torchaudio.info(wav_file).sample_rate
        start_frame = int(sample['start'] * sample_rate)
        end_frame = int(sample['end'] * sample_rate)
        waveform, _ = torchaudio.load(wav_file,
                                       num_frames=end_frame - start_frame,
                                       frame_offset=start_frame)
    else:
        waveform, sample_rate = torchaudio.load(wav_file)
    # del wav_file
    del sample['wav']
    sample['wav'] = waveform  # overwrite wav
    sample['sample_rate'] = sample_rate
    return sample'''

    old_librosa = '''def decode_wav(sample):
    """ Decode a wav file, convert bytes to waveform tensor.
        Inplace operation. Uses librosa + audioread for broad format support.

        Args:
            sample: {key, wav, ...}

        Returns:
            {key, wav, sample_rate, ...}
    """
    assert 'key' in sample
    assert 'wav' in sample
    wav_file = sample['wav']
    if isinstance(wav_file, bytes):
        wav_file = io.BytesIO(wav_file)
    elif hasattr(wav_file, 'seek'):
        wav_file.seek(0)
    if 'start' in sample:
        assert 'end' in sample
        offset = float(sample['start'])
        duration = float(sample['end']) - offset
        waveform, sample_rate = librosa.load(
            wav_file, sr=None, mono=True,
            offset=offset, duration=duration)
    else:
        waveform, sample_rate = librosa.load(wav_file, sr=None, mono=True)
    waveform = torch.from_numpy(waveform).unsqueeze(0)
    del sample['wav']
    sample['wav'] = waveform
    sample['sample_rate'] = sample_rate
    return sample'''

    if old_torchaudio in content:
        content = content.replace(old_torchaudio, new_func)
    elif old_librosa in content:
        content = content.replace(old_librosa, new_func)
    else:
        print("  ??? processor.py decode_wav (original not found)")
        return False

    with open(target, "w", encoding="utf-8") as f:
        f.write(content)
    print("  FIX processor.py decode_wav (-> soundfile)")
    return True


def patch_resample(wenet_root):
    """Fix: torchaudio.transforms.Resample -> librosa.resample."""
    target = os.path.join(wenet_root, "dataset", "processor.py")
    if not os.path.exists(target):
        return False

    with open(target, "r", encoding="utf-8") as f:
        content = f.read()

    old_lines = """    if sample_rate != resample_rate:
        sample['sample_rate'] = resample_rate
        sample['wav'] = torchaudio.transforms.Resample(
            orig_freq=sample_rate, new_freq=resample_rate)(waveform)"""

    new_lines = """    if sample_rate != resample_rate:
        sample['sample_rate'] = resample_rate
        waveform_np = waveform.squeeze(0).numpy()
        waveform_np = librosa.resample(
            y=waveform_np, orig_sr=sample_rate, target_sr=resample_rate)
        sample['wav'] = torch.from_numpy(waveform_np).unsqueeze(0)"""

    if new_lines in content:
        print("  OK  processor.py resample (already patched)")
        return False

    if old_lines not in content:
        print("  ??? processor.py resample (target not found)")
        return False

    content = content.replace(old_lines, new_lines)
    with open(target, "w", encoding="utf-8") as f:
        f.write(content)
    print("  FIX processor.py resample (torchaudio.transforms -> librosa)")
    return True


def patch_soundfile():
    """Fix: soundfile 0.12+ removed SoundFileRuntimeError, needed by librosa.resample."""
    try:
        import soundfile as sf
        if hasattr(sf, 'SoundFileRuntimeError'):
            print("  OK  soundfile.SoundFileRuntimeError (already exists)")
            return False
        sf.SoundFileRuntimeError = RuntimeError
        print("  FIX soundfile.SoundFileRuntimeError = RuntimeError")
        return True
    except ImportError:
        print("  SKIP soundfile (not installed)")
        return False


def main():
    print("=" * 50)
    print("  VoiceTextService — Applying compatibility patches")
    print("=" * 50)
    print()

    # Must apply soundfile patch BEFORE importing wenet (which imports librosa for resample)
    patch_soundfile()

    wenet_root = find_wenet_root()
    print(f"\n  wenet location: {wenet_root}\n")

    changed = False
    changed |= patch_conv2d_imports(wenet_root)
    changed |= patch_decode_wav(wenet_root)
    changed |= patch_resample(wenet_root)

    print()
    if changed:
        print("  Patches applied. You can now run start.bat")
    else:
        print("  All patches already applied. Ready to run.")
    print("=" * 50)


if __name__ == "__main__":
    main()
