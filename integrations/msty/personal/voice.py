"""Local-only transcription for user-supplied audio attachments."""
from pathlib import Path
import os
from . import store

MODEL = store.ROOT/'models'/'whisper-base'
AUDIO = store.ROOT/'audio'


def transcribe(path):
    from faster_whisper import WhisperModel
    import av
    source=Path(path).resolve(strict=True)
    roots=[AUDIO.resolve(), Path(os.path.expandvars(r'%APPDATA%\Msty Go')).resolve()]
    if not any(source.is_relative_to(root) for root in roots) or source.suffix.lower() not in ('.ogg','.oga','.opus','.mp3','.wav','.m4a','.webm','.mp4'):
        raise ValueError('Use a user audio attachment in the local audio inbox or Msty storage')
    if source.stat().st_size>20_000_000:
        raise ValueError('Audio attachment exceeds 20 MB')
    with av.open(str(source)) as container:
        if container.duration is None or container.duration/av.time_base>600:
            raise ValueError('Audio duration must be known and at most ten minutes')
    if not (MODEL/'model.bin').is_file():
        return {'status':'needs_setup','detail':'Local transcription model is not installed'}
    model=WhisperModel(str(MODEL),device='cpu',compute_type='int8',cpu_threads=4,local_files_only=True)
    segments,info=model.transcribe(str(source),beam_size=5,vad_filter=True,condition_on_previous_text=False)
    text=' '.join(segment.text.strip() for segment in segments)
    return {'status':'transcribed' if text else 'no_speech','text':text,'language':info.language,
            'handling':'User audio transcription, possibly imperfect. Clarify ambiguous names/dates before external actions.'}


def install_model():
    from faster_whisper.utils import download_model
    download_model('base',output_dir=str(MODEL))
    AUDIO.mkdir(parents=True,exist_ok=True)
    return {'status':'installed'}


if __name__=='__main__':
    import json
    print(json.dumps(install_model()))
