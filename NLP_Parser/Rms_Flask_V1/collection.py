'''
Collection of Functionality used in the Ratemyservice NLP
'''
class Collection():
    ''' Constructor Initialization '''
    def __init__(self):
        pass

    def __str__(self):
        return self.__class__.__name__

    def new_keys(self, subdriver_tags, stagwords):
        '''
        Input:
        -----
        subdriver_tags: DataFrame from the Database,
        stagwords: DataFrame from the Database

        Output:
        ------
        return Stagwords and Vector Binding of the Drivers
        '''
        qoc_keys = stagwords[stagwords['rate_param_id'] == 5]['stagword'].tolist()
        qoservice_keys = stagwords[stagwords['rate_param_id'] == 1]['stagword'].tolist()
        VfM_keys = stagwords[stagwords['rate_param_id'] == 4]['stagword'].tolist()
        QoStaff_keys = stagwords[stagwords['rate_param_id'] == 3]['stagword'].tolist()
        
        drivers_id = list(set(subdriver_tags.rate_param_id.tolist()))
        final_ids = [subdriver_tags.loc[subdriver_tags.rate_param_id.isin([id])].id.tolist() for id in drivers_id]
        new_dict = dict(zip(drivers_id, final_ids))
        return qoc_keys, qoservice_keys, VfM_keys, QoStaff_keys, new_dict


    def key_convert(self, li, subdriver_tags, rate_params):
        '''
        Input:
        -----
        li: Parsing containing data list,
        subdriver_tags: DataFrame from the Database,
        rate_params: Parameters of the Drivers

        Output:
        ------
        return List containing Polarity, Sub-Driver and Driver init.
        '''
        drivers_id = list(set(subdriver_tags.rate_param_id.tolist()))
        sub_drivers = rate_params.loc[rate_params.id.isin(drivers_id)].label.tolist()
        driver = dict(zip(drivers_id, sub_drivers))
        subdriver = {data[0]: data[2] for data in subdriver_tags.values.tolist()}
        try:
            li_new = [[i[0], subdriver[i[1]], driver[i[2]]] for i in li]
        except:
            li_new = [li[1], subdriver[li[4]], driver[li[3]]]
        return li_new


    def sent_part(self, text):
        '''
        Input:
        -----
        text: Review or Sentence

        Output:
        ------
        return List containing parts of the Review.
        '''
        return [i.strip() for i in text.replace(",", ".").lower().split(".") if i != ""]


    def key_search(self, sent, subdriver_tags, regex_data, keyword_test, rate_params, stagwords):
        '''
        Input:
        -----
        sent: Review or Sentence to be parsed,
        subdriver_tags: DataFrame from the Database,
        regex_data: DataFrame containing regex matching data from the Database,
        keyword_test: DataFrame containing Keyword or Phrases to check the Redundency,
        rate_params: DataFrame containing Mapping of the Drivers and Sub-Drivers,
        stagwords: DataFrame from the Database

        Output:
        ------
        return List containing Parsed Information.
        '''
        # Import the Required Library
        import re
        from nltk.corpus import stopwords
        from nltk import word_tokenize, FreqDist

        stopword = list(set(stopwords.words('english'))) + ['plus']
        sentence = self.sent_part(sent)

        qoc_keys, qoservice_keys, VfM_keys, QoStaff_keys, new_dict = self.new_keys(subdriver_tags, stagwords)

        driver_keys = {5: qoc_keys, 1: qoservice_keys, 3: QoStaff_keys, 4: VfM_keys}

        data = keyword_test.copy()  # Assigning DataTable Keyword_test to data

        sent_sent, sent_sent1 = [], []
        for sent in sentence:
            sent1 = []
            regex = [i for i in regex_data['keyword'].tolist() if len(re.findall(i, sent)) != 0]
            if sent != " ":
                sent = re.sub(r'[^a-z ]', "", sent)
                sent = " ".join([i for i in sent.split() if i not in stopword])
                word_token = word_tokenize(sent)
                search_list = []
                for i in word_token:
                    if i in qoc_keys: search_list.append(5)
                    if i in qoservice_keys: search_list.append(1)
                    if i in VfM_keys: search_list.append(4)
                    if i in QoStaff_keys: search_list.append(3)
                search_list = list(set(search_list))
                search_list = search_list + [0]

                for id in search_list:
                    if id != 0:
                        driver_word, clean_word, key1 = [], [], []
                        main_keys = driver_keys[id]
                        driver_word = []  # List which contains the word which is common in given word and sentence
                        for _i in word_token:
                            for _j in main_keys:
                                if re.search('\\b' + _j + '\\b', _i):
                                    if _j != "":
                                        driver_word.append(_j)
                        if len(driver_word) != 0:
                            driver_word = driver_word + [""]
                            clean_word = []
                            for i in word_token:
                                if i not in driver_word:
                                    clean_word.append(i)
                            for name in data['keyword'].tolist():
                                for j in driver_word:
                                    if j != "":
                                        if re.search('\\b' + j + '\\b', name):
                                            key1.append(name)
                            new_data = data.loc[data['keyword'].isin(key1)]
                            subid = list(set(new_data['tags_id'].tolist()))
                            textdata = data.loc[data['tags_id'].isin(subid)]
                            new_names = textdata['keyword'].tolist()
                            new_key = []
                            clean_word = clean_word
                            for name in new_names:
                                for j in clean_word:
                                    if j != "":
                                        if re.search('\\b' + j + '\\b', name):
                                            new_key.append(name)
                            textdata1 = textdata.loc[textdata['keyword'].isin(new_key)]
                            subdriver_id = textdata1['tags_id'].tolist()
                            subid_freq = dict(FreqDist(subdriver_id))

                            ids = [x[0] for x in sorted(subid_freq.items(), key=lambda x: x[1])[-1:]]
                        if len(ids) > 0:
                            for k, v in new_dict.items():
                                if ids[0] in v:
                                    sent1.append([sent, ids[0], k])
                sent_sent.extend(sent1)
                sent_sent1 = self.key_convert(sent_sent, subdriver_tags, rate_params)  # Data Table subdriver_tags
            if len(regex) == 1:
                data_regex = regex_data.loc[regex_data['keyword'].isin(regex)]
                data_regex = data_regex[['keyword', 'tags_id', 'rate_param_id']]
                data_regex = data_regex.values.tolist()
                return sent_sent1 + self.key_convert(data_regex, subdriver_tags, rate_params)  # Data Table subdriver_tags
        return sent_sent1


    def db_search(self, cur, sentence, clf, subdriver_tags, keyword_test, review_phrase, rate_params):
        '''
        Input:
        -----
        cur: DataBase Connection Cursor,
        sentence: Review or Sentence to be parsed,
        clf: Classifier for the Sentiment Analysis,
        subdriver_tags: DataFrame from the Database,
        keyword_test: DataFrame containing Keyword or Phrases to check the Redundency,
        review_phrase: DataFrame containing keywords or Phrases for Sentiment Analysis,
        rate_params: DataFrame containing Mapping of the Drivers and Sub-Drivers

        Output:
        ------
        return List containing Parsed Information.
        '''
        drivers = []
        for sent in self.sent_part(sentence):
            tokns = sent
            if tokns != "":
                # Import the Required Library
                from textblob import TextBlob
                
                blob = TextBlob(tokns.strip())
                blob_len = len(blob.split())
                ngblobs = []
                for i in range(1, blob_len+1):
                    bn1 = blob.ngrams(n=i)	# Ngram with 1 i.e., split every word into single word
                    bnf = [" ".join(bn.lower()).lower() for bn in bn1]
                    ngblobs.extend(bnf)
                for item in ngblobs:
                    resemble = keyword_test[keyword_test['keyword'] == item]
                    data = resemble.values.tolist()
                    if len(data) != 0:
                        data = data[0]
                        if data[2] == 'pos':
                            shi = 0.84345645456
                        elif data[2] == 'neg':
                            shi = -0.84345645456
                        else:
                            # Import the Required Library
                            from sentiment import SentimentAnalyzer

                            shi = SentimentAnalyzer(review_phrase).polarise_this(tokns.strip(), clf2=clf)
                        print(tokns.strip(), "--------------Check---------------", shi)

                        if len([i for i in tokns.strip().split(" ")]) < 6:
                            if shi > 0.850000:
                                cur.execute("SELECT * FROM review_phrase Where keyword = '{}'".format(tokns.strip()))
                                row = cur.fetchall()
                                if not row:
                                    query1 = """INSERT INTO review_phrase(keyword,rating)VALUES (%s, %s)"""
                                    cur.execute(query1, [tokns.strip(), 'pos'])
                            elif shi < -0.850000:
                                cur.execute("SELECT * FROM review_phrase Where keyword = '{}'".format(tokns.strip()))
                                row = cur.fetchall()
                                if not row:
                                    query1 = """INSERT INTO review_phrase(keyword,rating)VALUES (%s, %s)"""
                                    cur.execute(query1, [tokns.strip(), 'neg'])
                            else:
                                pass
                        new_data = self.key_convert(data, subdriver_tags, rate_params)
                        drivers.append([shi]+new_data)
        return drivers

