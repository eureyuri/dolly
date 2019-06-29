# https://qiita.com/saihara-k/items/86ba457523daa02c1869
# https://cloud.google.com/docs/authentication/getting-started?hl=ja

# https://cloud.google.com/speech-to-text/docs/streaming-recognize#speech-streaming-recognize-python
# https://cloud.google.com/speech-to-text/docs/multiple-voices

import re
import sys
import datetime

from google.cloud import speech_v1p1beta1 as speech
from google.cloud.speech_v1p1beta1 import enums
from google.cloud.speech_v1p1beta1 import types
import pyaudio
from six.moves import queue

import speech_recognition as sr

from nltk.corpus import stopwords
from sklearn.feature_extraction.text import TfidfVectorizer
import pandas as pd

# Audio recording parameters
RATE = 16000
CHUNK = int(RATE // 10)  # 100ms

LANGUAGE_CODE = 'en-US'
EXIT_COMMAND = r'\b(exit|quit)\b'

SPEAKER_COUNT = ""
SPEAKERS = []
STOPWORD_SET = {}
RANDOM_KEYWORDS_NUM = 5


class MicrophoneStream(object):
    """Opens a recording stream as a generator yielding the audio chunks."""

    def __init__(self, rate, chunk):
        self._rate = rate
        self._chunk = chunk

        # Create a thread-safe buffer of audio data
        self._buff = queue.Queue()
        self.closed = True

    def __enter__(self):
        self._audio_interface = pyaudio.PyAudio()
        self._audio_stream = self._audio_interface.open(
            format=pyaudio.paInt16,
            # TODO: Chennels
            channels=1,
            rate=self._rate,
            input=True,
            frames_per_buffer=self._chunk,
            # Run the audio stream asynchronously to fill the buffer object.
            # This is necessary so that the input device's buffer doesn't
            # overflow while the calling thread makes network requests, etc.
            stream_callback=self._fill_buffer,
        )

        self.closed = False

        return self

    def __exit__(self, type, value, traceback):
        self._audio_stream.stop_stream()
        self._audio_stream.close()
        self.closed = True
        # Signal the generator to terminate so that the client's
        # streaming_recognize method will not block the process termination.
        self._buff.put(None)
        self._audio_interface.terminate()

    def _fill_buffer(self, in_data, frame_count, time_info, status_flags):
        """Continuously collect data from the audio stream, into the buffer."""
        self._buff.put(in_data)
        return None, pyaudio.paContinue

    def generator(self):
        while not self.closed:
            # Use a blocking get() to ensure there's at least one chunk of
            # data, and stop iteration if the chunk is None (end of the stream)
            chunk = self._buff.get()
            if chunk is None:
                return
            data = [chunk]

            # Now consume whatever other data's still buffered.
            while True:
                try:
                    chunk = self._buff.get(block=False)
                    if chunk is None:
                        return
                    data.append(chunk)
                except queue.Empty:
                    break

            yield b''.join(data)


def listen_print_loop(responses):
    """
    The responses passed is a generator that will block until a response
    is provided by the server.

    Each response may contain multiple results, and each result may contain
    multiple alternatives; for details, see https://goo.gl/tjCPAU.  Here we
    print only the transcription for the top alternative of the top result.
    """
    num_chars_printed = 0
    output = ""
    for response in responses:
        if not response.results:
            continue

        # The `results` list is consecutive. For streaming, we only care about
        # the first result being considered, since once it's `is_final`, it
        # moves on to considering the next utterance.
        result = response.results[0]
        if not result.alternatives:
            continue

        # Display the transcription of the top alternative.
        transcript = result.alternatives[0].transcript

        # Display interim results, but with a carriage return at the end of the
        # line, so subsequent lines will overwrite them.
        # If the previous result was longer than this one, we need to print
        # some extra spaces to overwrite the previous result
        overwrite_chars = ' ' * (num_chars_printed - len(transcript))

        if not result.is_final:
            sys.stdout.write(transcript + overwrite_chars + '\r')
            sys.stdout.flush()

            num_chars_printed = len(transcript)

        else:
            speaker_num = result.alternatives[0].words[0].speaker_tag
            speaker = SPEAKERS[speaker_num - 1]

            output += speaker + transcript + overwrite_chars + "\n"
            print(output)

            # Exit recognition
            if re.search(EXIT_COMMAND, transcript, re.I):
                analyze_output(output)
                print()
                print('----- Thank you for using Dolly! -----')
                break

            num_chars_printed = 0


def analyze_output(output):
    word_num = word_count(output)

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
            print("Please select number to change")
            for i in range(SPEAKER_COUNT):
                print(str(i) + ": " + SPEAKERS[i])
            answer = input()
            if answer == "quit":
                switching = False
            try:
                answer = int(answer)
            except:
                continue
            if int(answer) < len(SPEAKERS):
                new_name = input("New name: ") + ": "
                old_name = SPEAKERS[answer]
                SPEAKERS[answer] = new_name
                output = output.replace(old_name, new_name)
                print("======")
                print(output)
                print("======")

    more_than_30 = []
    more_than_10 = []
    for word, count in word_num.items():
        if int(count) >= 30:
            more_than_30.append(word)
        elif 30 > int(count) >= 10:
            more_than_10.append(word)

    print()
    print("------")
    print("Mentioned more than 30 times:")
    print(more_than_30)

    print("------")
    print("Mentioned more than 10 times:")
    print(more_than_10)

    print("------")
    import warnings
    warnings.filterwarnings('ignore')
    print("Dolly's random suggestions:")
    tfidf_vectorizer = TfidfVectorizer(analyzer='word', stop_words=sorted(list(STOPWORD_SET.union(name.strip(': ') for name in SPEAKERS))))
    tfidf_vectors = tfidf_vectorizer.fit_transform([output])
    first_tfidf_vector = tfidf_vectors[0]
    random_keywords = pd.DataFrame(first_tfidf_vector.T.todense(), index=tfidf_vectorizer.get_feature_names(), columns=["tfidf"])
    random_keywords = random_keywords.sort_values(by=["tfidf"], ascending=False)
    # print(random_keywords)
    global RANDOM_KEYWORDS_NUM
    print(random_keywords.head(RANDOM_KEYWORDS_NUM).index.tolist())
    print("------")

    print()
    print("Exporting transcript...")
    output += "\n------\n Mentioned more than 30 times: " + str(more_than_30) + "\n------\n Mentioned more than 10 times: " + str(more_than_10) + "\n------\n Dolly's random suggestions: " + str(random_keywords.head(RANDOM_KEYWORDS_NUM).index.tolist()) + "\n------\n"

    now = datetime.datetime.now()
    now = now.strftime("%Y-%m-%d_%H:%M")

    f = open("output/" + now + ".txt", "x")
    f.write(output)
    f.close()

    print("======")
    print("Finished exporting")
    print("======")


def word_count(output):
    global STOPWORD_SET
    STOPWORD_SET = set(stopwords.words('english'))
    STOPWORD_SET = STOPWORD_SET.union(set(speaker.strip() for speaker in SPEAKERS))

    word_num = {}
    for word in output.lower().split():
        if word not in STOPWORD_SET:
            if word not in word_num:
                word_num[word] = 1
            else:
                word_num[word] += 1

    return word_num


def main():
    client = speech.SpeechClient()
    config = types.RecognitionConfig(
        encoding=enums.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=RATE,
        language_code=LANGUAGE_CODE,
        enable_speaker_diarization=True,
        diarization_speaker_count=SPEAKER_COUNT)
    streaming_config = types.StreamingRecognitionConfig(
        config=config,
        interim_results=True)
    # indicates that this stream request should return temporary results
    # that may be refined at a later time (after processing more audio).
    # Interim results will be noted within responses through the setting of
    # is_final to false

    with MicrophoneStream(RATE, CHUNK) as stream:
        audio_generator = stream.generator()
        requests = (types.StreamingRecognizeRequest(audio_content=content)
                    for content in audio_generator)

        responses = client.streaming_recognize(streaming_config, requests)

        # Now, put the transcription responses to use.
        listen_print_loop(responses)


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


def short_response(choices):
    r = sr.Recognizer()

    while True:
        with sr.Microphone() as source:
            audio = r.listen(source)
        try:
            answer = r.recognize_google(audio).lower()
            print(answer)
            if str(answer).lower() in choices:
                return answer
        except:
            pass


# def long_response():
#     chunk = 1024  # Record in chunks of 1024 samples
#     sample_format = pyaudio.paInt16  # 16 bits per sample
#     channels = 2
#     fs = 44100  # Record at 44100 samples per second
#     # seconds = 3
#     filename = "output.wav"
#
#     p = pyaudio.PyAudio()  # Create an interface to PortAudio
#
#     print('Recording...')
#
#     stream = p.open(format=sample_format,
#                     channels=channels,
#                     rate=fs,
#                     frames_per_buffer=chunk,
#                     input=True)
#
#     frames = []  # Initialize array to store frames
#
#     # Store data in chunks for 3 seconds
#     while True:
#         try:
#             data = stream.read(chunk)
#             frames.append(data)
#         except KeyboardInterrupt():
#             break
#     # for i in range(0, int(fs / chunk * seconds)):
#     #     data = stream.read(chunk)
#     #     frames.append(data)
#
#     # Stop and close the stream
#     stream.stop_stream()
#     stream.close()
#     # Terminate the PortAudio interface
#     p.terminate()
#
#     print('Finished recording')
#
#     # Save the recorded data as a WAV file
#     wf = wave.open(filename, 'wb')
#     wf.setnchannels(channels)
#     wf.setsampwidth(p.get_sample_size(sample_format))
#     wf.setframerate(fs)
#     wf.writeframes(b''.join(frames))
#     wf.close()
#
#     f = wave.open(filename, "rb")
#


if __name__ == '__main__':
    instructions()
    print("Dolly is litening...")
    print()
    main()


# Attempt: Does not work for streaming
# https://www.youtube.com/watch?v=jc_-AIYvfKs
# https://pypi.org/project/SpeechRecognition/
# import speech_recognition as sr
#
# r = sr.Recognizer()
#
# while True:
#     try:
#         with sr.Microphone() as source:
#             print("Start!")
#             audio = r.listen(source)
#
#         try:
#             print("Google thinkgs you said: " + r.recognize_google(audio))
#         except:
#             pass
#     except KeyboardInterrupt():
#         break
#     print("Bye!")
