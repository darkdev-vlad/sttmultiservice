import os
import json
import sys

from google.cloud import speech_v1p1beta1 as _speech_beta
from google.cloud.speech_v1p1beta1 import enums as _enums_beta
from google.cloud.speech_v1p1beta1 import types as _types_beta

from google.cloud import speech as _speech
from google.cloud.speech import enums as _enums
from google.cloud.speech import types as _types


class GlobalConfig(object):
    language_code = "en-US"
    required_env_variables = {}

    @classmethod
    def load_variables(cls):
        for key,value in cls.required_env_variables.items():
            if key not in os.environ:
                print(json.dumps({'error': "Environment variable \"{!s}\" is not set".format(key)}))
                sys.exit(0)
            else:
                setattr(cls, value, os.environ[key])


class WitASR(GlobalConfig):
    API_ENDPOINT = 'https://api.wit.ai/speech'

    access_token = None

    required_env_variables = {
        'WIT_ASR_ACCESS_TOKEN': 'access_token'
    }


class YandexASR(GlobalConfig):
    split_by_silence = True
    service_account_id = None
    key_id = None
    private_cert = None
    folder_id = None
    required_env_variables = {
        'YANDEX_ASR_SERVICE_ACCOUNT_ID': 'service_account_id',
        'YANDEX_ASR_KEY_ID': 'key_id',
        'YANDEX_ASR_PRIVATE_CERT': 'private_cert',
        'YANDEX_ASR_FOLDER_ID': 'folder_id'
    }


class GoogleASR(GlobalConfig):
    api_file = None
    project_name = None
    confidence = False
    use_beta = False
    split_by_channels = False
    automatic_punctuation = False
    enable_speaker_diarization = False
    diarization_speaker_count = False
    phrases_list = []
    api_data = {}
    required_env_variables = {
        'GOOGLE_APPLICATION_CREDENTIALS': 'api_file',
        'GOOGLE_APPLICATION_PROJECT_NAME': 'project_name'
    }

    class GoogleLibs(object):
        speech = None
        enums = None
        types = None

        def __init__(self, speech_lib, types_lib, enums_lib):
            self.speech = speech_lib
            self.types = types_lib
            self.enums = enums_lib

    @staticmethod
    def get_libs():
        if GoogleASR.use_beta:
            google_libs = GoogleASR.GoogleLibs(_speech_beta, _types_beta, _enums_beta)
        else:
            google_libs = GoogleASR.GoogleLibs(_speech, _types, _enums)

        return google_libs

    @staticmethod
    def __load_api_data():
        try:
            with open(os.path.abspath(GoogleASR.api_file)) as f:
                GoogleASR.api_data = json.load(f)
        except IOError as err:
            print(json.dumps({'error': "Caught error \"{0!s}\" in file {1!s}".format(err.strerror, err.filename)}))
            sys.exit(0)

    @classmethod
    def load_variables(cls):
        super(GoogleASR, cls).load_variables()
        GoogleASR.__load_api_data()
