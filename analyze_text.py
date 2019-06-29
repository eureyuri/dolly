from nltk.corpus import stopwords
from sklearn.feature_extraction.text import TfidfVectorizer
import pandas as pd

import warnings


class AnalyzeText:
    def __init__(self, speakers, speaker_count, random_keywords_count):
        self.speakers = speakers
        self.speaker_count = speaker_count
        self.stopword_set = set(stopwords.words('english'))
        self.stopword_set = self.stopword_set.union(
            set(speaker.strip() for speaker in self.speakers))
        self.random_keywords_count = random_keywords_count

    def word_count(self, output):
        word_num = {}
        for word in output.lower().split():
            if word not in self.stopword_set:
                if word not in word_num:
                    word_num[word] = 1
                else:
                    word_num[word] += 1

        return word_num

    def analyze(self, output):
        word_num = self.word_count(output)

        more_than_30 = []
        more_than_10 = []
        for word, count in word_num.items():
            if int(count) >= 30:
                more_than_30.append(word)
            elif 30 > int(count) >= 10:
                more_than_10.append(word)

        warnings.filterwarnings('ignore')
        tfidf_vectorizer = TfidfVectorizer(analyzer='word',
                                           stop_words=sorted(
                                               list(self.stopword_set.union(
                                                   name.strip(': ')
                                                   for name in self.speakers)))
                                           )
        tfidf_vectors = tfidf_vectorizer.fit_transform([output])
        first_tfidf_vector = tfidf_vectors[0]
        random_keywords = pd.DataFrame(first_tfidf_vector.T.todense(),
                                       index=tfidf_vectorizer.
                                       get_feature_names(),
                                       columns=["tfidf"])
        random_keywords = random_keywords.sort_values(by=["tfidf"],
                                                      ascending=False)
        random_keywords = random_keywords.head(
            self.random_keywords_count).index.tolist()

        return more_than_30, more_than_10, random_keywords
