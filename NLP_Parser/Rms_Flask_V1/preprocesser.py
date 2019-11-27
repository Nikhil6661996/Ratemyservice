'''
Pre-processing of the Data for the Ratemyservice NLP
'''
from re import sub

class Cleaner():
    ''' Constructor Initialization '''
    def __init__(self):
        self.sub = sub

    def __str__(self):
        return self.__class__.__name__

    def clean_text(self, text):
        ''' Pre-Processing of the text '''
        text = self.sub(r"can't", "cannot", text)
        text = self.sub(r"won't", "will not", text)
        text = self.sub(r"want's", "wants", text)
        text = self.sub(r"when'd", "when did", text)
        text = self.sub(r"can'tif", "cannot if", text)
        text = self.sub(r"y'know", "you know", text)
        text = self.sub(r"y'all", "you all", text)
        text = self.sub(r"y'think", "you think", text)
        text = self.sub(r"d'you", "do you", text)

        text = self.sub(r"\'s", " is", text)
        text = self.sub(r"\'d", " had", text)
        text = self.sub(r"n't", " not", text)
        text = self.sub(r"\'ve", " have", text)
        text = self.sub(r"\'ll", " will", text)
        text = self.sub(r"\'m", " am", text)
        text = self.sub(r"\'re", " are", text)
        text = self.sub(r"\'ve", " have", text)

        text = self.sub(r"can’t", "cannot", text)
        text = self.sub(r"won’t", "will not", text)
        text = self.sub(r"want’s", "wants", text)
        text = self.sub(r"when’d", "when did", text)
        text = self.sub(r"can’tif", "cannot if", text)
        text = self.sub(r"y’know", "you know", text)
        text = self.sub(r"y’all", "you all", text)
        text = self.sub(r"y’think", "you think", text)
        text = self.sub(r"d’you", "do you", text)

        text = self.sub(r"\’s", " is", text)
        text = self.sub(r"\’d", " had", text)
        text = self.sub(r"n’t", " not", text)
        text = self.sub(r"\’ve", " have", text)
        text = self.sub(r"\’ll", " will", text)
        text = self.sub(r"\’m", " am", text)
        text = self.sub(r"\’re", " are", text)
        text = self.sub(r"\’ve", " have", text)

        return text
