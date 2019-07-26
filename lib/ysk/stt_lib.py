import time
import jwt
import requests
import json
import os
import pytz
from datetime import datetime
from dateutil.parser import parse

import grpc

import lib.ysk.stt_service_pb2 as stt_service_pb2
import lib.ysk.stt_service_pb2_grpc as stt_service_pb2_grpc


class YandexIAM:
    JWT_URL = 'https://iam.api.cloud.yandex.net/iam/v1/tokens'
    IAM_FILE_NAME = os.path.abspath(os.path.dirname(__file__) + "/iam_data.json")

    service_account_id = None
    key_id = None
    private_key = None

    def __init__(self, service_account_id: str, key_id: str, private_key_filename: str):
        self.service_account_id = service_account_id
        self.key_id = key_id
        self.read_private_key_file(private_key_filename)

    def read_private_key_file(self, private_key_filename: str):
        with open(private_key_filename, 'r') as private:
            self.private_key = private.read()
            private.close()

    def generate_jwt(self) -> str:
        now = int(time.time())
        payload = {
            'aud': self.JWT_URL,
            'iss': self.service_account_id,
            'iat': now,
            'exp': now + 360}

        encoded_token = jwt.encode(
            payload,
            self.private_key,
            algorithm='PS256',
            headers={'kid': self.key_id})

        return encoded_token.decode("utf-8")

    def generate_iam(self):
        encoded_token = self.generate_jwt()

        r = requests.post(self.JWT_URL, data=json.dumps({'jwt': encoded_token}),
                          headers={"Content-Type": "application/json"})

        if isinstance(r.content, bytes):
            content = r.content.decode("utf-8")
        else:
            content = r.content

        if r.status_code == 200:
            return json.loads(content)
        else:
            return {"error": content}

    @staticmethod
    def get_iam():
        """
        Get IAM token or read from JSON file
        :return: IAM token string
        :rtype: int
        """
        if os.path.exists(YandexIAM.IAM_FILE_NAME) and os.path.isfile(YandexIAM.IAM_FILE_NAME):
            try:
                json_iam = json.load(open(YandexIAM.IAM_FILE_NAME, "r"))

                expires = parse(json_iam['expiresAt']).replace(tzinfo=pytz.UTC)
                now = datetime.utcnow().replace(tzinfo=pytz.UTC)

                if now < expires:
                    return json_iam['iamToken']
                else:
                    return None
            except json.JSONDecodeError:
                return None

    @staticmethod
    def save_iam(iam_json_dict: dict):
        json.dump(iam_json_dict, open(YandexIAM.IAM_FILE_NAME, "w"))


class YandexSTT:
    CHUNK_SIZE = 16000

    @staticmethod
    def gen(folder_id, audio_file_name, language_code: str):
        specification = stt_service_pb2.RecognitionSpec(
            language_code=language_code,
            profanity_filter=True,
            model='general',
            partial_results=True,
            audio_encoding='LINEAR16_PCM',
            sample_rate_hertz=8000
        )
        streaming_config = stt_service_pb2.RecognitionConfig(specification=specification, folder_id=folder_id)

        yield stt_service_pb2.StreamingRecognitionRequest(config=streaming_config)

        with open(audio_file_name, 'rb') as f:
            data = f.read(YandexSTT.CHUNK_SIZE)
            while data != b'':
                yield stt_service_pb2.StreamingRecognitionRequest(audio_content=data)
                data = f.read(YandexSTT.CHUNK_SIZE)

    @staticmethod
    def run(folder_id, iam_token, audio_file_name, language_code: str):
        cred = grpc.ssl_channel_credentials()
        channel = grpc.secure_channel('stt.api.cloud.yandex.net:443', cred)
        stub = stt_service_pb2_grpc.SttServiceStub(channel)

        it = stub.StreamingRecognize(YandexSTT.gen(folder_id, audio_file_name, language_code),
                                     metadata=(('authorization', 'Bearer %s' % iam_token),))

        strings_answer = []
        error = None
        try:
            for r in it:
                try:
                    if r.chunks[0].final:
                        strings_answer.append(r.chunks[0].alternatives[0].text)
                except LookupError:
                    print('Not available chunks')
        except grpc._channel._Rendezvous as err:
            error = err

        return "\n".join(strings_answer)
