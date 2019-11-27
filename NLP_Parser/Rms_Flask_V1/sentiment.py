'''
Sentiment Analyzer and Classifier for the Ratemyservice NLP
'''
import gc as garbage

class SentimentAnalyzer():
    ''' Constructor Initialization '''
    def __init__(self, review_phrase):
        self.garbage = garbage
        self.review_phrase = review_phrase

    def __str__(self):
        return self.__class__.__name__

    def cl_dump(self):
        ''' Classifier for the Polarity Check and Sentiment Analyzer '''
        self.garbage.disable()
        import numpy as np
        from textblob.classifiers import NaiveBayesClassifier

        trainies = self.review_phrase.tail(int(len(self.review_phrase) / 11))
        trainies = trainies.sort_values('id', ascending=[0])
        data_train = trainies[['keyword', 'rating']].values.tolist()
        trains = [[str(item[0]), item[1]] for item in data_train]
        clf = NaiveBayesClassifier(np.array(trains))
        self.garbage.enable()
        return clf

    def polarise_this(self, tokn, clf2=None):
        '''
        Input:
        -----
        data: Text as Sentence or Phrase

        Output:
        ------
        return Polarity depends on the Sentiment of the Text
        '''
        self.garbage.disable()
        if clf2 is None:
            clf2 = self.cl_dump(self.review_phrase)

        prob_dist = clf2.prob_classify(tokn)
        self.garbage.enable()
        return prob_dist.prob("pos") - prob_dist.prob("neg")
