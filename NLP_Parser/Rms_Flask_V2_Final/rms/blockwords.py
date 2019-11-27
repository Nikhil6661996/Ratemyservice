''' 
BlockWords Detection for the Ratemyservice NLP
'''

class VulgurPrevent():
    ''' Constructor Initialization '''
    def __init__(self, wordlist):
        '''
        wordlist : Set of Vulgur Words or Phrases
        '''
        self.wordlist = wordlist

    def __str__(self):
        return self.__class__.__name__

    def profanity_filter(self, text):
        '''
        Input:
        -----
        data: Text to check the Vulgur Words

        Output:
        ------
        return Replaced Vulgur Words in the Text
        '''
        blockwords = self.wordlist.blockword.tolist()
        data = text.split(".")
        brokenstr = []
        for text1 in data:
            brokenstr.extend(text1.split())
        badwordmask = '********************************************'
        newtext = ''
        for word in brokenstr:
            if word in blockwords:
                newtext = text.replace(word, badwordmask[:len(word)])
        return newtext
