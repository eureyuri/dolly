# https://qiita.com/saihara-k/items/86ba457523daa02c1869
# https://cloud.google.com/docs/authentication/getting-started?hl=ja

# https://cloud.google.com/speech-to-text/docs/streaming-recognize#speech-streaming-recognize-python
# https://cloud.google.com/speech-to-text/docs/multiple-voices

import datetime

import speech_to_text
import analyze_text

START_COMMAND = ["hey dolly", "hey, dolly"]
AVAILABLE_LANGUAGE = ["english", "korean", "japanese", "chinese"]
SAMPLE_RATE = 16000
CHUNK = int(SAMPLE_RATE // 10)  # 100ms
RANDOM_KEYWORDS_COUNT = 5


def instructions():
    print()
    print("Starting Dolly...\n")

    print("Start recording with 'Hey Dolly!'")
    speech_to_text.SpeechToText().short_response(START_COMMAND)
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
        language = input("Enter either " + user_language[:-2] + ": ")
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


def output_and_modification(output, speakers, speaker_count):
    print("------")
    print("Dolly heard:")
    print(output)
    print("------")

    switch = ""
    while switch != "y" and switch != "n":
        print()
        switch = input("Would you like to switch the speaker names? (y/n): ").lower()

    if switch == "y":
        switching = True
        while switching:
            print()
            print("Type quit to continue")
            print()
            print("Please select valid number to change")
            for i in range(speaker_count):
                print(str(i) + ": " + speakers[i])
            answer = input()
            if answer == "quit":
                switching = False
            try:
                answer = int(answer)
            except:
                continue

            if int(answer) < len(speakers):
                new_name = input("New name: ") + ": "
                old_name = speakers[answer]
                speakers[answer] = new_name
                output = output.replace(old_name, new_name)
                print("======")
                print(output)
                print("======")


def print_export_analysis(output, more_than_30, more_than_10, random_keywords):
    print()
    print("------")
    print("Mentioned more than 30 times:")
    print(more_than_30)

    print("------")
    print("Mentioned more than 10 times:")
    print(more_than_10)

    print("------")
    print("Dolly's random suggestions:")
    print(random_keywords)
    print("------")

    print()
    print("Exporting transcript...")
    print()

    output += "\n------\n Mentioned more than 30 times: " + str(more_than_30) + "\n------\n Mentioned more than 10 times: " + str(more_than_10) + "\n------\n Dolly's random suggestions: " + str(random_keywords) + "\n------\n"

    now = datetime.datetime.now()
    now = now.strftime("%Y-%m-%d_%H:%M")

    f = open("output/" + now + ".txt", "x")
    f.write(output)
    f.close()

    print("======")
    print("Finished exporting")
    print("======")


def run(language_code, exit_command, speaker_count, speakers):
    global SAMPLE_RATE, CHUNK

    config = speech_to_text.SpeechToTextConfig(speakers, speaker_count, SAMPLE_RATE, CHUNK, language_code, exit_command)

    short_or_long = ""
    while short_or_long not in ['y', 'n']:
        short_or_long = input("Will your meeting be over 5 minutes? (y/n): ").lower()

    if short_or_long == 'n':
        text = speech_to_text.SpeechToText(config).short_stream_meet()
    elif short_or_long == 'y':
        time = ""
        while not isinstance(time, int):
            time = input("Approximately, how long will your meeting be?: ")
            try:
                time = int(time)
            except:
                continue
        text = speech_to_text.SpeechToText(config).long_asynchronous_meet(seconds=time)

    output_and_modification(text, config.speakers, config.speaker_count)

    more_than_30, more_than_10, random_keywords = analyze_text.AnalyzeText(speakers=config.speakers, speaker_count=config.speaker_count, random_keywords_count=RANDOM_KEYWORDS_COUNT).analyze(text)
    print_export_analysis(text, more_than_30, more_than_10, random_keywords)


if __name__ == '__main__':
    language_code, exit_command, speaker_count, speakers = instructions()

    print("Dolly is litening...")
    print()

    run(language_code, exit_command, speaker_count, speakers)

    print()
    print('----- Thank you for using Dolly! -----')
