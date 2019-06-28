


def instructions():
    print()
    print("Starting Dolly...\n")

    print("Start recording with 'Hey Dolly!'")
    short_response(["hey dolly", "hey, dolly"])
    print()

    print("----- Welcome to Dolly! -----")
    print()
    print("Which language will your meeting be in?")
    language = ""
    while language not in ["english", "korean", "japanese", "chinese"]:
        language = input("Enter either English, Korean, Japanese, Chinese: ")
        language = language.lower()
        # TODO
        # print("Enter either English, Korean, Japanese, Chinese: ")
        # language = short_response(["english", "korean", "japanese", "chinese"])

    global LANGUAGE_CODE
    global EXIT_COMMAND
    if language == "english":
        LANGUAGE_CODE = "en-US"
        EXIT_COMMAND = r'\b(exit|quit)\b'
        print()
        print("End program with exit or quit")
    elif language == "korean":
        LANGUAGE_CODE = "ko-KR"
        EXIT_COMMAND = r'\b(떠나다|휴가)\b'
        print()
        print("End program with 떠나다 or 휴가")
    elif language == "japanese":
        LANGUAGE_CODE = "ja-JP"
        EXIT_COMMAND = r'\b(終了|やめる)\b'
        print()
        print("End program with 終了 or やめる")
    elif language == "chinese":
        LANGUAGE_CODE = "zh"
        EXIT_COMMAND = r'\b(放弃|退出)\b'
        print()
        print("End program with 放弃 or 退出")

    global SPEAKER_COUNT
    while not isinstance(SPEAKER_COUNT, int):
        print()
        SPEAKER_COUNT = input("How many people are at your meeting today? ")
        try:
            SPEAKER_COUNT = int(SPEAKER_COUNT)
        except:
            continue

    global SPEAKERS
    for i in range(SPEAKER_COUNT):
        SPEAKERS.append(input("Input person " + str(i + 1) + "'s name: ") + ": ")


if __name__ == '__main__':
    instructions()
    print("Dolly is litening...")
    print()
    main()
