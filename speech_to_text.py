import datetime
import pyaudio
from six.moves import queue
import wave

import re
import sys

from google.cloud import speech_v1p1beta1 as speech
from google.cloud.speech_v1p1beta1 import enums
from google.cloud.speech_v1p1beta1 import types
from google.cloud import storage
import speech_recognition as sr


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


class SpeechToTextConfig:
    def __init__(self, speakers, speaker_count, sample_rate, chunk, language_code, exit_command):
        self.speakers = speakers
        self.speaker_count = speaker_count
        self.sample_rate = sample_rate
        self.chunk = chunk
        self.language_code = language_code
        self.exit_command = exit_command

        self.client = speech.SpeechClient()
        self.recognition_config = types.RecognitionConfig(
            encoding=enums.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=self.sample_rate,
            language_code=self.language_code,
            enable_speaker_diarization=True,
            diarization_speaker_count=self.speaker_count)
        self.streaming_config = types.StreamingRecognitionConfig(
            config=self.recognition_config,
            interim_results=True)
        # indicates that this stream request should return temporary results
        # that may be refined at a later time (after processing more audio).
        # Interim results will be noted within responses through the setting of
        # is_final to false


class SpeechToText:
    def __init__(self, config=None):
        self.config = config

    def short_stream_meet(self):
        with MicrophoneStream(self.config.sample_rate, self.config.chunk) as stream:
            audio_generator = stream.generator()
            requests = (types.StreamingRecognizeRequest(audio_content=content)
                        for content in audio_generator)

            responses = self.config.client.streaming_recognize(self.config.streaming_config, requests)

            # Now, put the transcription responses to use.
            return self.listen_print_loop(responses)

    def listen_print_loop(self, responses):
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
                speaker = self.config.speakers[speaker_num - 1]

                output += speaker + transcript + overwrite_chars + "\n"
                print(output)

                # Exit recognition
                if re.search(self.config.exit_command, transcript, re.I):
                    return output

                num_chars_printed = 0

    def short_response(self, choices):
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

    def long_asynchronous_meet(self, seconds, sample_format=pyaudio.paInt16, channels=1):
        p = pyaudio.PyAudio()

        stream = p.open(format=sample_format,
                        channels=channels,
                        rate=self.config.sample_rate,
                        frames_per_buffer=self.config.chunk,
                        input=True)

        frames = []

        for i in range(0, int(self.config.sample_rate / self.config.chunk * seconds)):
            data = stream.read(self.config.chunk)
            frames.append(data)

        stream.stop_stream()
        stream.close()
        p.terminate()

        # Save the recorded data as a WAV file
        print("Exporting...")
        now = datetime.datetime.now()
        now = now.strftime("%Y-%m-%d_%H:%M")
        filename = "output/audio_long_meeting/" + now + ".wav"
        wf = wave.open(filename, 'wb')
        wf.setnchannels(channels)
        wf.setsampwidth(p.get_sample_size(sample_format))
        wf.setframerate(self.config.sample_rate)
        wf.writeframes(b''.join(frames))
        wf.close()

        print("Uploading to Google Cloud...")
        storage_client = storage.Client.from_service_account_json('Dolly-secret.json')
        bucket = storage_client.get_bucket("dolly-long-audio")
        blob = bucket.blob(filename)
        blob.upload_from_filename(filename)

        return self.long_transcribe_gcs(gcs_uri="gs://" + "dolly-long-audio" + "/" + filename)

    def long_transcribe_gcs(self, gcs_uri):
        print("Transcribing... (This may take a while)")
        audio = types.RecognitionAudio(uri=gcs_uri)

        operation = self.config.client.long_running_recognize(self.config.recognition_config, audio)

        response = operation.result(timeout=90)

        # Each result is for a consecutive portion of the audio. Iterate through
        # them to get the transcripts for the entire audio file.
        text = ""
        for result in response.results:
            speaker_num = result.alternatives[0].words[0].speaker_tag
            speaker = self.config.speakers[speaker_num - 1]

            text += speaker + result.alternatives[0].transcript + '\n'
            # The first alternative is the most likely one for this portion.
            # print(u'Transcript: {}'.format(result.alternatives[0].transcript))
            # print('Confidence: {}'.format(result.alternatives[0].confidence))

        return text
