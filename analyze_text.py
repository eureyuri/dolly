import datetime

from nltk.corpus import stopwords
from sklearn.feature_extraction.text import TfidfVectorizer
import pandas as pd


class AnalyzeText:
    def __init__(self, speakers, speaker_count):
        self.speakers = speakers
        self.speaker_count = speaker_count
        self.stopword_set = set(stopwords.words('english'))
        self.stopword_set = self.stopword_set.union(set(speaker.strip() for speaker in self.speakers))
        self.random_keywords_count = 5

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
                for i in range(self.speaker_count):
                    print(str(i) + ": " + self.speakers[i])
                answer = input()
                if answer == "quit":
                    switching = False
                try:
                    answer = int(answer)
                except:
                    continue
                if int(answer) < len(self.speakers):
                    new_name = input("New name: ") + ": "
                    old_name = self.speakers[answer]
                    self.speakers[answer] = new_name
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
        tfidf_vectorizer = TfidfVectorizer(analyzer='word', stop_words=sorted(list(self.stopword_set.union(name.strip(': ') for name in self.speakers))))
        tfidf_vectors = tfidf_vectorizer.fit_transform([output])
        first_tfidf_vector = tfidf_vectors[0]
        random_keywords = pd.DataFrame(first_tfidf_vector.T.todense(), index=tfidf_vectorizer.get_feature_names(), columns=["tfidf"])
        random_keywords = random_keywords.sort_values(by=["tfidf"], ascending=False)

        print(random_keywords.head(self.random_keywords_count).index.tolist())
        print("------")

        print()
        print("Exporting transcript...")
        output += "\n------\n Mentioned more than 30 times: " + str(more_than_30) + "\n------\n Mentioned more than 10 times: " + str(more_than_10) + "\n------\n Dolly's random suggestions: " + str(random_keywords.head(self.random_keywords_count).index.tolist()) + "\n------\n"

        now = datetime.datetime.now()
        now = now.strftime("%Y-%m-%d_%H:%M")

        f = open("output/" + now + ".txt", "x")
        f.write(output)
        f.close()

        print("======")
        print("Finished exporting")
        print("======")
