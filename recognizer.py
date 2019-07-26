#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
from lib.recognizers import *

parser = argparse.ArgumentParser(description='Convert speech to text via various services (Google, Yandex, Wit)')
parser.add_argument('--file', '-f', dest='file', required=True,
                    help='Path to media file for recognition')
parser.add_argument('--method', '-m', dest='method', default='google',
                    help='Recognition method (google, yandex, wit) '
                         'default "google"')
parser.add_argument('--language-code', '-lc', dest='language_code', default='en-US',
                    help='Language code, default en-US')
parser.add_argument('--split-by-silence', '-ss', dest='split_by_silence', default='0',
                    help='Split audio by silence for better recognition (Yandex) (0 or 1) default 1')
parser.add_argument('--use-beta', '-b', dest='beta', default='1',
                    help='Use BETA libraries for Google (0 or 1) default 1')
parser.add_argument('--confidence', '-c', dest='confidence', default='1',
                    help='Output confidence for Google recognition (BETA) (0 or 1) default 1')
parser.add_argument('--split-by-channels', '-s', dest='split_by_channels', default='0',
                    help='Split dialog by channels for Google recognition (0 or 1) default 0')
parser.add_argument('--auto-punctuation', '-p', dest='auto_punctuation', default='0',
                    help='Enable automatic punctuation (BETA) (Google) (0 or 1) default 0', )
parser.add_argument('--phrases-file', '-pf', dest='phrases_file', default='0',
                    help='File for phrase hints (Google) (0 or file path) default 0', )

yes_list = ['1', 'true', 'y', 'yes']

args = parser.parse_args()
file = args.file
method = args.method
GlobalConfig.language_code = args.language_code
YandexASR.split_by_silence = args.split_by_silence.lower() in yes_list
GoogleASR.confidence = args.confidence.lower() in yes_list
GoogleASR.use_beta = args.beta.lower() in yes_list
GoogleASR.split_by_channels = args.split_by_channels.lower() in yes_list
GoogleASR.automatic_punctuation = args.auto_punctuation.lower() in yes_list

if args.phrases_file != "0" and os.path.isfile(args.phrases_file):
    with open(os.path.abspath(args.phrases_file), 'r') as phrases_file:
        GoogleASR.phrases_list = phrases_file.read().split("\n")


def recognize(file_name, method_name):
    try:
        file_object = os.path.abspath(file_name)
        if not os.path.isfile(file_object):
            raise IOError("File doesn't exists")
    except IOError as err:
        return {'error': "Caught error \"" + err.strerror + "\" in file " + err.filename}

    type_name = method_name

    operations = {
        'yandex': type_yandex,
        'google': type_google,
        'wit': type_wit
    }

    if type_name in operations:
        result = operations[type_name](file_object)
        if not result:
            return {'error': 'Empty result was returned'}
        else:
            return result
    else:
        return {'error': 'Unknown recognition method'}


if __name__ == "__main__":
    result_rec = recognize(file, method)
    print(json.dumps(result_rec))
