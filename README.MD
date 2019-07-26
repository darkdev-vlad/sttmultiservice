## Description
This utility helps to recognize speech from audio files through multiple services. Right now STTMultiservice can work with:
- Google Cloud Speech-To-Text
- Yandex SpeechKit
- Wit.ai

STTMultiservice main purpose is to recognize dialogs from phone calls.

## Get started

### Preparing

Please note, this app requires Python 3 (tested with Python 3.6 and 3.7) and won't run on versions, that are earlier.

You will need libmagic for STT multiservice. Read the installation article [here](https://github.com/ahupp/python-magic/blob/master/README.md#installation).

STTMultiservice also requires ffmpeg. Consider [this](https://github.com/adaptlearning/adapt_authoring/wiki/Installing-FFmpeg) article to install it.  

Clone this repository using command:

    $ git clone {REPO_URL_HERE}
    
### Configuration
    
Specify environment variables (for example, in .bash_profile):
```
GOOGLE_APPLICATION_CREDENTIALS - path to JSON file from Google Cloud
GOOGLE_APPLICATION_PROJECT_NAME - Google Cloud project name

YANDEX_ASR_SERVICE_ACCOUNT_ID - service account id from Yandex Cloud
YANDEX_ASR_KEY_ID - key id, obtained for specified service account
YANDEX_ASR_FOLDER_ID - folder id, for which have permission to read and write specified service account
YANDEX_ASR_PRIVATE_CERT - path to private certificate for specified service account (PEM file)

WIT_ASR_ACCESS_TOKEN - access token for Wit.ai application 
```

#### Google Cloud Speech-To-Text
To get JSON file with credentials read [this](https://cloud.google.com/speech-to-text/docs/quickstart-client-libraries#before-you-begin) article.
You only need to follow first step of "Before you begin".

#### Yandex SpeechKit
To get all required credentials from Yandex consider [this](https://cloud.yandex.com/docs/speechkit/quickstart#before-begin) article.
Follow steps for service account, right now STTMultiservice works only with it. You just need to get required credentials and private certificate. STTMultiservice will obtain IAM token by itself.

#### Wit.ai
Follow [this](https://wit.ai/docs/quickstart) article to create application. Please note, you can specify language only in your application for Wit recognition. Next, get "Server Access Token
" on your application's settings page.   

**Please note - you only need to configure services, which you will use.**

### Usage

Make sure, that your default interpreter is Python 3. In another cases add "python3" (or something like this) in the beginning of the command.
To run recognition use this command:

    $ ./recognizer.py -f=PATH_TO_FILE_FOR_RECOGNITION
    
To get more help run

    $ ./recognizer.py --help
    
Right now you can only get answer in JSON format.