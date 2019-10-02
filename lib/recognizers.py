import magic
import io
import subprocess
from uuid import uuid4
from .google_streaming import GoogleStorageUploader
from .credentials import *
from pydub import AudioSegment
from .ysk.stt_lib import *

global_strings = []
global_yandex_align_time = 0
global_yandex_already_processed = False


def type_google(file_name: str):
    GoogleASR.load_variables()

    google_libs = GoogleASR.get_libs()
    speech = google_libs.speech
    enums = google_libs.enums
    types = google_libs.types

    google_client = GoogleStorageUploader(GoogleASR.project_name, GoogleASR.api_data['project_id'])
    phrases_hints = [speech.types.SpeechContext(
        phrases=GoogleASR.phrases_list)]

    file_name = os.path.abspath(file_name)
    audio_info = AudioSegment.from_file(file_name)

    mime = magic.Magic(mime=True)
    content_type = mime.from_file(file_name)

    # Instantiates a client
    client = speech.SpeechClient()

    amr_encoding = enums.RecognitionConfig.AudioEncoding.AMR

    if content_type == 'audio/amr':
        if audio_info.frame_rate == 8000:
            amr_encoding = enums.RecognitionConfig.AudioEncoding.AMR
        elif audio_info.frame_rate == 16000:
            amr_encoding = enums.RecognitionConfig.AudioEncoding.AMR_WB

    allowed_formats = {
        'audio/x-wav': types.RecognitionConfig(
            encoding=enums.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=audio_info.frame_rate,
            speech_contexts=phrases_hints,
            language_code=GoogleASR.language_code),
        'audio/ogg': types.RecognitionConfig(
            encoding=enums.RecognitionConfig.AudioEncoding.OGG_OPUS,
            sample_rate_hertz=audio_info.frame_rate,
            speech_contexts=phrases_hints,
            language_code=GoogleASR.language_code),
        'video/ogg': types.RecognitionConfig(
            encoding=enums.RecognitionConfig.AudioEncoding.OGG_OPUS,
            sample_rate_hertz=audio_info.frame_rate,
            speech_contexts=phrases_hints,
            language_code=GoogleASR.language_code),
        'audio/flac': types.RecognitionConfig(
            encoding=enums.RecognitionConfig.AudioEncoding.FLAC,
            sample_rate_hertz=audio_info.frame_rate,
            speech_contexts=phrases_hints,
            language_code=GoogleASR.language_code),
        'audio/amr': types.RecognitionConfig(
            encoding=amr_encoding,
            sample_rate_hertz=audio_info.frame_rate,
            speech_contexts=phrases_hints,
            language_code=GoogleASR.language_code)
    }

    blob = None

    if content_type in allowed_formats:
        config = allowed_formats[content_type]
    else:
        return {
            'error': 'Unsupported audio format or count of audio channels is more than 1.'
                     'If you want to use more channels, type --use-beta=1'}
    if audio_info.duration_seconds < 60:
        # Loads the audio into memory
        with io.open(file_name, 'rb') as audio_file:
            content = audio_file.read()
            audio = types.RecognitionAudio(content=content)
    else:
        blob = google_client.upload_file(file_name)
        audio = {'uri': "gs://" + blob.bucket.name + "/" + blob.name}

    config.enable_word_time_offsets = True
    config.enable_separate_recognition_per_channel = GoogleASR.split_by_channels
    config.audio_channel_count = audio_info.channels

    if GoogleASR.use_beta:
        config.enable_word_confidence = GoogleASR.confidence
        config.enable_automatic_punctuation = GoogleASR.automatic_punctuation

        if GoogleASR.enable_speaker_diarization:
            config.enable_speaker_diarization = GoogleASR.enable_speaker_diarization
            if GoogleASR.diarization_speaker_count > 0:
                config.diarization_speaker_count = GoogleASR.diarization_speaker_count

    # Detects speech in the audio file
    operation = client.long_running_recognize(config, audio)
    strings = []

    response = operation.result(timeout=1000)

    for result in response.results:
        alternative = result.alternatives[0]
        text = alternative.transcript

        words = []

        for word_info in alternative.words:
            word = word_info.word
            start_time = word_info.start_time
            end_time = word_info.end_time

            word_object_to_append = {
                'word': word,
                'start_time': {
                    'seconds': start_time.seconds,
                    'nanos': start_time.nanos
                },
                'end_time': {
                    'seconds': end_time.seconds,
                    'nanos': end_time.nanos
                }
            }

            if GoogleASR.use_beta:
                if GoogleASR.confidence and hasattr(word_info, 'confidence'):
                    word_object_to_append['confidence'] = word_info.confidence

            words.append(word_object_to_append)

        text_object = {
            'text': text,
            'words': words
        }

        if GoogleASR.use_beta:
            if GoogleASR.confidence and hasattr(alternative, 'confidence'):
                text_object['confidence'] = alternative.confidence

        if GoogleASR.split_by_channels and hasattr(result, 'channel_tag'):
            text_object['channel_tag'] = result.channel_tag

        strings.append(text_object)

    if blob:
        google_client.delete_file(blob)

    return strings


def read_audio(file_name):
    # function to read audio(wav) file
    with open(file_name, 'rb') as f:
        audio = f.read()
    return audio


def split_by_ffmpeg(input_file: str, noise_level=-30, duration=0.5, search_text="[silencedetect"):
    """
    Split audio file by silence and get all silence parts and audio parts duration
    :param input_file:
    :param noise_level:
    :param duration:
    :param search_text:
    :return:
    """
    current_dir_path = os.path.dirname(os.path.realpath(__file__))
    dir_name = os.path.abspath(current_dir_path + "/../temp")
    base_name = os.path.splitext(os.path.basename(input_file))[0]
    tmp_file_audio = dir_name + "/tmp_" + str(uuid4()) + "_" + base_name + "_"

    if not os.path.isdir(os.path.abspath(dir_name)) or not os.path.exists(os.path.abspath(dir_name)):
        os.mkdir(os.path.abspath(dir_name))

    # Get silence from audio
    get_silence_command = [
        r'ffmpeg',
        '-i', input_file,
        '-af', 'silencedetect=noise=' + str(noise_level) + "dB:d=" + str(duration),
        '-f', 'null',
        '-'
    ]

    proc = subprocess.Popen(get_silence_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = proc.communicate()

    text = err.decode("utf-8")
    lines = text.split("\n")

    parts = []
    index = 0

    for line in lines:
        if search_text in line:
            values_list = line.split("] ")
            data = values_list[1]
            if "start" in data:
                val_list = data.split(": ")
                value = val_list[1]
                parts.append({"start": value})
            elif "end" in data:
                val_list = data.split(" | ")
                vals = val_list[0]
                val_list = vals.split(": ")
                value = val_list[1]
                parts[index]["end"] = value
                index += 1

    file_parts = []

    index = 0
    while index < len(parts):
        idx = str(index + 1)
        split_command = None
        start = 0

        if index == 0 and float(parts[index]['start']) > 0:
            start = 0
            end = float(parts[index]['start'])
            split_command2 = [
                r'ffmpeg',
                '-ss', str(start),
                '-t', str(end),
                '-i', input_file,
                tmp_file_audio + str(index) + ".wav"
            ]
            proc_opened = subprocess.Popen(split_command2, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            proc_opened.communicate()
            file_parts.append({
                "index": index,
                "file_name": tmp_file_audio + str(index) + ".wav",
                "start": 0,
                "end": end
            })

        if index + 1 < len(parts):
            start = float(parts[index]['end']) - 0.25
            end = float(parts[index + 1]['start']) - float(parts[index]['end']) + 2 * 0.25
            split_command = [
                r'ffmpeg',
                '-ss', str(start),
                '-t', str(end),
                '-i', input_file,
                tmp_file_audio + idx + ".wav"
            ]
        elif 'end' in parts[index]:
            start = float(parts[index]['end']) - 0.25
            split_command = [
                r'ffmpeg',
                '-ss', str(start),
                '-i', input_file,
                tmp_file_audio + idx + ".wav"
            ]

        index += 1

        if split_command:
            proc_opened = subprocess.Popen(split_command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            proc_opened.communicate()
            file_parts.append({
                "index": int(idx),
                "file_name": tmp_file_audio + idx + ".wav",
                "start": str(start),
            })

    return file_parts


def type_wit(file_name: str):
    WitASR.load_variables()

    file_name = os.path.abspath(file_name)
    # reading audio
    audio = read_audio(file_name)

    audio_info = AudioSegment.from_file(file_name)

    available_content_types = {
        "audio/x-mpeg-3": "audio/mpeg3",
        "audio/x-wav": "audio/wav",
        "audio/ulaw": "audio/ulaw"
    }

    mime = magic.Magic(mime=True)
    content_type = mime.from_file(file_name)

    if content_type in available_content_types:
        content_type = available_content_types[content_type]
    else:
        return {'error': "Unsupported audio format"}

    if audio_info.duration_seconds > 13:
        return {'error': 'Files with duration more than 13 seconds are not supported yet'}

    # defining headers for HTTP request
    headers = {'authorization': 'Bearer ' + WitASR.access_token,
               'Content-Type': content_type}

    # making an HTTP post request
    resp = requests.post(WitASR.API_ENDPOINT, headers=headers,
                         data=audio)

    # converting response content to JSON format
    data = json.loads(resp.content.decode("utf-8"))

    # get text from data
    if not '_text' in data and 'error' in data:
        return {'error': data['error']}
    else:
        return [data['_text']]


def type_yandex(file_name: str):
    YandexASR.load_variables()

    iam_key = YandexIAM.get_iam()

    if not iam_key:
        yandex_iam = YandexIAM(YandexASR.service_account_id, YandexASR.key_id, YandexASR.private_cert)
        iam = yandex_iam.generate_iam()
        yandex_iam.save_iam(iam)
        iam_key = iam['iamToken']

    file = os.path.abspath(file_name)

    if YandexASR.split_by_silence:
        audio_parts = split_by_ffmpeg(file)
        delete = True
    else:
        audio_parts = [{
            "index": 1,
            "file_name": file,
            "start": 0
        }]
        delete = False

    strings = []
    for audio_file in audio_parts:
        try:
            text = YandexSTT.run(YandexASR.folder_id, iam_key, audio_file['file_name'], YandexASR.language_code)

            if text != "":
                strings.append({
                    "text": text,
                    "audio_part_start_time": audio_file['start']
                })
        except Exception as error:
            err = str(error)
        finally:
            if delete:
                os.remove(audio_file['file_name'])

    return strings
