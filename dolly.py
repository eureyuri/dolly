# https://qiita.com/saihara-k/items/86ba457523daa02c1869
# https://cloud.google.com/docs/authentication/getting-started?hl=ja

# https://cloud.google.com/speech-to-text/docs/streaming-recognize#speech-streaming-recognize-python
# https://cloud.google.com/speech-to-text/docs/multiple-voices

import speech_to_text
import analyze_text

STOPWORD_SET = {}

AVAILABLE_LANGUAGE = ["english", "korean", "japanese", "chinese"]


def instructions():
    print()
    print("Starting Dolly...\n")

    print("Start recording with 'Hey Dolly!'")
    speech_to_text.SpeechToText().short_response(["hey dolly", "hey, dolly"])
    print()

    print("----- Welcome to Dolly! -----")
    print()
    print("Which language will your meeting be in?")

    global AVAILABLE_LANGUAGE
    language = ""
    while language not in AVAILABLE_LANGUAGE:
        user_language = ""
        for lang in AVAILABLE_LANGUAGE:
            user_language += lang + "  "
        language = input("Enter either " + user_language + ": ")
        language = language.lower()
        # TODO
        # print("Enter either English, Korean, Japanese, Chinese: ")
        # language = short_response(["english", "korean", "japanese", "chinese"])

    if language == "english":
        language_code = "en-US"
        exit_command = r'\b(exit|quit)\b'
        print()
        print("End program with exit or quit")
    elif language == "korean":
        language_code = "ko-KR"
        exit_command = r'\b(떠나다|휴가)\b'
        print()
        print("End program with 떠나다 or 휴가")
    elif language == "japanese":
        language_code = "ja-JP"
        exit_command = r'\b(終了|やめる)\b'
        print()
        print("End program with 終了 or やめる")
    elif language == "chinese":
        language_code = "zh"
        exit_command = r'\b(放弃|退出)\b'
        print()
        print("End program with 放弃 or 退出")

    speaker_count = ""
    while not isinstance(speaker_count, int):
        print()
        speaker_count = input("How many people are at your meeting today? ")
        try:
            speaker_count = int(speaker_count)
        except:
            continue

    speakers = []
    for i in range(speaker_count):
        speakers.append(input("Input person " + str(i + 1) + "'s name: ") + ": ")

    return language_code, exit_command, speaker_count, speakers


if __name__ == '__main__':
    language_code, exit_command, speaker_count, speakers = instructions()

    print("Dolly is litening...")
    print()

    sample_rate = 16000
    chunk = int(sample_rate // 10)  # 100ms

    config = speech_to_text.SpeechToTextConfig(speakers, speaker_count, sample_rate, chunk, language_code, exit_command)
    text = speech_to_text.SpeechToText(config).execute()

    analyze_text.AnalyzeText(speakers=config.speakers, speaker_count=config.speaker_count).analyze(text)
    print()
    print('----- Thank you for using Dolly! -----')
