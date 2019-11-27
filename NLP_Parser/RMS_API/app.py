try:
    # MAKE ALL THE MODULES AVAILABLE
    import sys
    import os
    import gc  # Garbage Collector
    import re
    import datetime

    import mysql.connector as MySQLdb

    import pandas as pd
    import numpy as np
    from pytz import timezone

    import nltk
    from nltk.corpus import stopwords
    from nltk.stem import WordNetLemmatizer
    from textblob import TextBlob
    from textblob.classifiers import NaiveBayesClassifier
    from nltk.tokenize.punkt import PunktTrainer
    from sklearn.externals import joblib

    from flask import Flask
    from flask import request, jsonify
    from werkzeug.contrib.fixers import ProxyFix

    trainer = PunktTrainer()
    trainer.INCLUDE_ALL_COLLOCS = True

    print("All the Modules are Successfully Imported")
except Exception as e:
    # PLEASE IMPORT THE MODULES FIRST
    print("Enable to import all the necessary Modules---", e)
    sys.exit()


def db_conn():
    try: connection = MySQLdb.connect(host="localhost",
                                       port=3306, database="ratemyservice_training_new", user="cdoshi", password="cdosh!1234")
    except: connection = MySQLdb.connect(host="localhost",
                                          port=3306, database="ratemyservice_training_new", user="cdoshi",
                                          password="cdosh!1234")
    return connection

conn = db_conn()
cur = conn.cursor()

subdriver_tags = pd.read_sql_query("SELECT * FROM tags", conn)
keyword_test = pd.read_sql_query("SELECT * FROM keywords", conn)
regex_data = pd.read_sql_query("SELECT * FROM keywords WHERE keyword LIKE '%.+%';", conn)
blockwords = pd.read_sql_query("SELECT * FROM blockwords", conn)
review_phrase = pd.read_sql_query("SELECT * FROM review_phrase", conn)
rate_params = pd.read_sql_query("SELECT * FROM rate_params", conn)
stagwords = pd.read_sql_query("SELECT * FROM stagwords", conn)

def profanityFilter(text, wordlist):
    blockwords = wordlist.blockword.tolist()
    data = text.split(".")
    brokenStr1 = []
    for text1 in data:
        brokenStr1.extend(text1.split())
    badWordMask = '********************************************'
    newtext = ''
    for word in brokenStr1:
        if word in blockwords:
            newtext = text.replace(word, badWordMask[:len(word)])
    return newtext

def cl_dump():
    gc.disable()
    trainies = review_phrase.tail(int(len(review_phrase) / 12))
    trainies.sort_values('id', ascending=[0], inplace=True)
    data_train = trainies[['keyword', 'rating']].values.tolist()
    trains = [[str(item[0]), item[1]] for item in data_train]
    clf = NaiveBayesClassifier(np.array(trains))
    joblib.dump(clf, 'my_model.pkl', compress=3)
    gc.enable()
    return clf

def cl_load():
    gc.disable()
    try:
        clf = joblib.load('my_model.pkl')
    except:
        clf = cl_dump()
    gc.enable()
    return clf

def polarise_this(tokn, clf2=None):
    gc.disable()
    if clf2 == None: clf2 = cl_load()
    try:
        prob_dist = clf2.prob_classify(tokn)
    except:
        prob_dist = clf2.prob_classify(tokn)
    gc.enable()
    return prob_dist.prob("pos") - prob_dist.prob("neg")

clf = cl_load()

application = Flask(__name__)

# app.wsgi_app = ProxyFix(app.wsgi_app)

def new_keys(subdriver_tags):
    QoC_keys = """Information,Report,reports,record,records,Document,documents,data,statement,
        statements,detail,details,detailed,deliverable,deliverables,receipt,receipts,form,
        forms,Advice,Advise,communication,communicate,suggestion,suggestions,notify,notification,
        explain,explained,answered,clear communication,clear,answer,terms,respond,network,email,
        phone,mobile,sms,internet,call,app,text,texts,duplicate,online,""".lower().split(',')
    QoService_keys = """duplicate,ATM,invoicing,experience,loyal,spread,switch,firm,company,
        agency,brand,card,Reliable,regular,consistent,call,contact,help line,shop,branch,helpdesk,
        outlets,home,workshop,event,first time,contract,credit,cash,machine,payment,waiting,
        wait,treatment,service,services,impressed,""".lower().split(',')
    VfM_keys = """product,spares,parts,investment,equipment,replacement,stock,Accessories,rate,
        cost,offer,bonus,incentives,premium,loan,package,returns,benifits,value,ROI,growth,
        scheme,cost,gift,complementary,reward,discount,promotion,promotional,loyalty points,deal,
        sale,policy,food,signal,goods,expensive,costly,charges,price,prices,pricing""".lower().split(',')
    QoStaff_keys = """Staff,team,technician,guy,workers,person,agent,customer care,queue,
        mechanic,people,apologise,professional,reception,understand,understanding,""".lower().split(',')
    drivers_id = list(set(subdriver_tags.rate_param_id.tolist()))
    final_ids = [subdriver_tags.loc[subdriver_tags.rate_param_id.isin([id])].id.tolist() for id in drivers_id]
    new_dict = dict(zip(drivers_id, final_ids))
    return QoC_keys, QoService_keys, VfM_keys, QoStaff_keys, new_dict

def key_convert(li, subdriver_tags, rate_params):
    drivers_id = list(set(subdriver_tags.rate_param_id.tolist()))
    sub_drivers = rate_params.loc[rate_params.id.isin(drivers_id)].label.tolist()
    driver = dict(zip(drivers_id, sub_drivers))
    subdriver = {data[0]: data[2] for data in subdriver_tags.values.tolist()}
    try:
        li_new = [[i[0], subdriver[i[1]], driver[i[2]]] for i in li]
    except:
        li_new = [li[1], subdriver[li[4]], driver[li[3]]]
    return li_new

sent_part = lambda text: [i.strip() for i in text.replace(",", ".").lower().split(".") if i != ""]

def key_search(sent, subdriver_tags, regex_data, keyword_test):
    stopword = list(set(stopwords.words('english'))) + ['plus']
    sentence = sent_part(sent)
    QoC_keys, QoService_keys, VfM_keys, QoStaff_keys, new_dict = new_keys(subdriver_tags)
    driver_keys = {5: QoC_keys, 1: QoService_keys, 3: QoStaff_keys, 4: VfM_keys}

    data = keyword_test.copy()  # Assigning DataTable Keyword_test to data

    sent_sent, sent_sent1 = [], []
    for index, sent in enumerate(sentence):
        sent1 = []
        regex = [i for i in regex_data['keyword'].tolist() if len(re.findall(i, sent)) != 0]
        if sent != " ":
            sent = re.sub(r'[^a-z ]', "", sent)
            sent = " ".join([i for i in sent.split() if i not in stopword])
            word_token = nltk.word_tokenize(sent)
            search_list = []
            for i in word_token:
                if i in QoC_keys: search_list.append(5)
                if i in QoService_keys: search_list.append(1)
                if i in VfM_keys: search_list.append(4)
                if i in QoStaff_keys: search_list.append(3)
            search_list = list(set(search_list))
            search_list = search_list + [0]

            for id in search_list:
                if id != 0:
                    driver_word, clean_word, names, key1 = [], [], [], []
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
                        subid_freq = dict(nltk.FreqDist(subdriver_id))

                        ids = [x[0] for x in sorted(subid_freq.items(), key=lambda x: x[1])[-1:]]
                    if len(ids) > 0:
                        for k, v in new_dict.items():
                            if ids[0] in v:
                                sent1.append([sent, ids[0], k])
            sent_sent.extend(sent1)
            sent_sent1 = key_convert(sent_sent, subdriver_tags, rate_params)  # Data Table subdriver_tags
        if len(regex) == 1:
            data_regex = regex_data.loc[regex_data['keyword'].isin(regex)]
            data_regex = data_regex[['keyword', 'tags_id', 'rate_param_id']]
            data_regex = data_regex.values.tolist()
            return sent_sent1 + key_convert(data_regex, subdriver_tags, rate_params)  # Data Table subdriver_tags
    return sent_sent1

def db_search(sent):
    drivers = []
    for sent in sent_part(sent):
        tokns = sent
        if tokns != "":
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
                    shi = polarise_this(tokns.strip(), clf2=clf)
                    print(tokns.strip(), "--------------Check---------------", shi)

                    if len([i for i in tokns.strip().split(" ")]) < 6:
                        if shi > 0.850000:
                            cur.execute("SELECT * FROM review_phrase Where keyword = '{}'".format(tokns.strip()))
                            row = cur.fetchall()
                            if not row:
                                query1 = """INSERT INTO review_phrase(keyword,rating)VALUES (%s, %s)"""
                                cur.execute(query1, [tokns.strip(), 'pos'])
                                conn.commit()
                        elif shi < -0.850000:
                            cur.execute("SELECT * FROM review_phrase Where keyword = '{}'".format(tokns.strip()))
                            row = cur.fetchall()
                            if not row:
                                query1 = """INSERT INTO review_phrase(keyword,rating)VALUES (%s, %s)"""
                                cur.execute(query1, [tokns.strip(), 'neg'])
                                conn.commit()
                        else:
                            pass
                    new_data = key_convert(data, subdriver_tags, rate_params)
                    drivers.append([shi]+new_data)
    return drivers

def file_check():
    # Current time in UTC
    print("In the Removal File Function-------------------------------------")
    try:
        now_utc = datetime.datetime.now(timezone('UTC'))
        day = now_utc.strftime("%d")
        if int(datetime.datetime.now().weekday()) == 6:
            if str(day) in ['01', '02', '03', '04', '05', '06', '07']:
                hour = int(now_utc.strftime("%H")) + 3
                if hour == 12:
                    os.remove("my_model.pkl")
                    print("---------File Removed----------------")
    except:
        pass

# Junk Cleaning from the Text
def clean_text(text):
    text = re.sub(r"can't","cannot",text)
    text = re.sub(r"won't","will not",text)
    text = re.sub(r"want's","wants",text)
    text = re.sub(r"when'd","when did",text)
    text = re.sub(r"can'tif","cannot if",text)
    text = re.sub(r"y'know","you know",text)
    text = re.sub(r"y'all","you all",text)
    text = re.sub(r"y'think","you think",text)
    text = re.sub(r"d'you","do you",text)

    text = re.sub(r"\'s"," is",text)
    text = re.sub(r"\'d"," had",text)
    text = re.sub(r"n't"," not",text)
    text = re.sub(r"\'ve"," have",text)
    text = re.sub(r"\'ll"," will",text)
    text = re.sub(r"\'m"," am",text)
    text = re.sub(r"\'re"," are",text)
    text = re.sub(r"\'ve"," have",text)

    text = re.sub(r"can’t","cannot",text)
    text = re.sub(r"won’t","will not",text)
    text = re.sub(r"want’s","wants",text)
    text = re.sub(r"when’d","when did",text)
    text = re.sub(r"can’tif","cannot if",text)
    text = re.sub(r"y’know","you know",text)
    text = re.sub(r"y’all","you all",text)
    text = re.sub(r"y’think","you think",text)
    text = re.sub(r"d’you","do you",text)

    text = re.sub(r"\’s"," is",text)
    text = re.sub(r"\’d"," had",text)
    text = re.sub(r"n’t"," not",text)
    text = re.sub(r"\’ve"," have",text)
    text = re.sub(r"\’ll"," will",text)
    text = re.sub(r"\’m"," am",text)
    text = re.sub(r"\’re"," are",text)
    text = re.sub(r"\’ve"," have",text)

    return text

@application.route("/", methods=['GET', 'POST'])
def home():
    gc.enable()
    cl = cl_load()
    file_check()        # Checking for the file Renewal
    json = request.json
    print(json)
    print()
    review_id = int(request.json['reviewId'])
    orating = int(request.json['LikeliRecommend'])
    qoc = int(request.json['QualityCommunication'])
    qoservice = int(request.json['QualityService'])
    qostaff = int(request.json['QualityStaff'])
    vfm = int(request.json['ValueForMoney'])
    review = request.json['Comments']

    if review.lower() == 'this is not a visible question hence should not be included in the calculation':
        if orating != 0 and qoc != 0 and qoservice != 0 and qostaff != 0:
            query1 = """INSERT INTO model_results(review_header_id, result, additional_comments)VALUES (%s, %s, %s)"""
            cur.execute(query1, [review_id, "Accepted", "Accepted with no review text"])
            conn.commit()
            # conn.close()
            return jsonify({'Accepted': 'Accepted with no review text'})
        else:
            query1 = """INSERT INTO model_results(review_header_id,result, additional_comments)VALUES (%s, %s, %s)"""
            cur.execute(query1, [review_id, "Accepted", "Accepted with no review text and incomplete ratings"])
            conn.commit()
            # conn.close()
            return jsonify({'Accepted': 'Accepted with no review text and incomplete ratings'})
    else:
        review = " ".join([clean_text(text) for text in review.split(" ")])
        word_lemma = WordNetLemmatizer()
        review = " ".join([word_lemma.lemmatize(word, pos="v") for word in review.split(" ")])

        data = []
        for sent in review.split('.'):
            sent = sent.strip()
            if len([i for i in sent.split()]) > 50:
                for j in sent.split('but'):
                    data.append(j.strip())
            else:
                data.append(sent)

        review = ".".join(data)

        if orating < 1:
            orating = 7
        else:
            pass
        if qoc < 1:
            qoc = 3
        else:
            pass
        if qoservice < 1:
            qoservice = 3
        else:
            pass
        if qostaff < 1:
            qostaff = 3
        else:
            pass
        if vfm < 1:
            vfm = 3
        else:
            pass


        dict1 = {}
        drivers = db_search(review)
        subdrivers = [item[2] for item in drivers]

        for item in range(len(subdrivers)):
            if subdrivers[item] not in list(dict1.keys()):
                dict1[subdrivers[item]] = [drivers[item]]
            else:
                dict1[subdrivers[item]] += [drivers[item]]

        final = []
        for item in dict1:
            if len(dict1[item]) == 1:
                shi = dict1[item][0][0]
                final.append(dict1[item][0])
            else:
                shi = sum([value[0] for value in dict1[item]])
                d = dict1[item][0]
                d[0] = shi
                final.append(d)

        ritesh = []

        for sentence in sent_part(review):
            for item in key_search(sentence, subdriver_tags, regex_data, keyword_test):
                if len(item) != 0:
                    shi = polarise_this(sentence, clf2=clf)
                    item = [shi] + item
                    ritesh.append(item)

        found_subdriver = [item[2] for item in ritesh]
        for item in final:
            print(item, "-----------------Item")
            print()
            if item[2] in found_subdriver:
                print(str(item[2]), "-------------------Item2")
                print()
                found_subdriver.remove(str(item[2]))

        for entry in ritesh:
            for exist in found_subdriver:
                if exist != entry[2]:
                    final.append(entry)

        for i in final:
            print(i, "----Final")

        proied = profanityFilter(review, blockwords)  # Check for block words in the Review

        if "*" in proied:
            query1 = """INSERT INTO model_results(review_header_id,result, additional_comments)VALUES (%s, %s, %s)"""
            cur.execute(query1, [review_id, "Rejected Because of Blockwords", proied])
            conn.commit()
            return jsonify({'Block': proied})

        confirmlist1, confirmlist2, confirmlist3 = [], [], []
        well_done_ids, improvement_ids = [], []
        if len(final) == 1:
            final = final + []
        if len(final) != 0:
            for data in final:
                if len(data) != 0:
                    shi = data[0]
                    skey_name = str.capitalize(str(data[2]))
                    skey_thing = str.capitalize(str(data[3]))
                    skey_lisi = [skey_thing, " >> ", skey_name]
                    skey_name1 = ' '.join(skey_lisi)
                    aspect = {"Quality of communication": int(qoc), "Quality of service": int(qoservice),
                              "Quality of staff": int(qostaff), "Value for money": int(vfm)}
                    print(aspect[skey_thing], "-------------------", type(aspect[skey_thing]))
                    print(shi, "-------------------", type(shi))
                    print(orating, "-------------------", type(orating))
                    if shi < 0.200000 and shi > -0.200000:
                        shi = 0.000000

                    print(shi, "-------------------", type(shi))
                    if (aspect[skey_thing] >= 3 and shi >= 0.000000 and orating >= 9) or (
                            aspect[skey_thing] <= 3 and shi <= 0.000000 and orating <= 6) or (
                                aspect[skey_thing] >= 3 and shi >= 0.000000 and orating == 7) or (
                                    aspect[skey_thing] >= 3 and shi >= 0.000000 and orating == 8) or (
                                        aspect[skey_thing] <= 3 and shi <= 0.000000 and orating == 7) or (
                                            aspect[skey_thing] <= 3 and shi <= 0.000000 and orating == 8):

                        if shi == 0.000000:
                            if aspect[skey_thing] >= 3 and orating > 7:
                                confirmlist2.append(" ".join([str.capitalize(skey_name1)]))
                                well_done_ids.append(skey_name)
                            elif aspect[skey_thing] > 3 and orating >= 7:
                                confirmlist2.append(" ".join([str.capitalize(skey_name1)]))
                                well_done_ids.append(skey_name)
                            elif aspect[skey_thing] <= 3 and orating <= 7:
                                confirmlist3.append(" ".join([str.capitalize(skey_name1)]))
                                improvement_ids.append(skey_name)
                            elif aspect[skey_thing] > 3 and orating < 7:
                                confirmlist1.append(" ".join([str.capitalize(skey_name1)]))
                                confirmlist3.append(" ".join([str.capitalize(skey_name1)]))
                                improvement_ids.append(skey_name)
                            elif aspect[skey_thing] < 3 and orating > 7:
                                confirmlist1.append(" ".join([str.capitalize(skey_name1)]))
                                confirmlist3.append(" ".join([str.capitalize(skey_name1)]))
                                improvement_ids.append(skey_name)
                            else:
                                pass
                        else:
                            if aspect[skey_thing] >= 3 and shi > 0.000000:
                                confirmlist2.append(" ".join([str.capitalize(skey_name1)]))
                                well_done_ids.append(skey_name)
                            elif aspect[skey_thing] <= 3 and shi < 0.000000:
                                confirmlist3.append(" ".join([str.capitalize(skey_name1)]))
                                improvement_ids.append(skey_name)
                            elif aspect[skey_thing] >= 3 and shi < 0.000000:
                                confirmlist1.append(" ".join([str.capitalize(skey_name1)]))
                                confirmlist3.append(" ".join([str.capitalize(skey_name1)]))
                                improvement_ids.append(skey_name)
                            elif aspect[skey_thing] <= 3 and shi > 0.000000:
                                confirmlist1.append(" ".join([str.capitalize(skey_name1)]))
                                confirmlist3.append(" ".join([str.capitalize(skey_name1)]))
                                improvement_ids.append(skey_name)
                            else:
                                pass
                    else:
                        confirmlist1.append(" ".join([str.capitalize(skey_name1)]))
                        confirmlist3.append(" ".join([str.capitalize(skey_name1)]))
                        improvement_ids.append(skey_name)

        if len(confirmlist1) == 0 and len(confirmlist2) == 0 and len(confirmlist3) == 0:
            query1 = """INSERT INTO model_results(review_header_id,result,additional_comments)VALUES (%s, %s, %s)"""
            cur.execute(query1, [review_id, "Accepted", "Rejected as review contain no meaning"])
            conn.commit()
            # conn.close()
            return jsonify({'additional_comment' : "Rejected as review contain no meaning"})
        well_done_id, improvement_id = [], []

        if len(well_done_ids) > 0 or len(improvement_ids) > 0:
            if len(well_done_ids) > 0:
                for text in well_done_ids:
                    well_done_id.append(str(subdriver_tags[subdriver_tags.tag == text].values.tolist()[0][0]))

            if len(improvement_ids) > 0:
                improvement_id = [str(subdriver_tags[subdriver_tags.tag == text].values.tolist()[0][0]) for text in
                                  improvement_ids]
            print(confirmlist1, "--------------Confirm")
            print(well_done_id, "-----------------well_done_id")
            print(improvement_id, "---------------------improvement_id")
            if len(confirmlist1) > 0:
                if len(well_done_id) > 0 and len(improvement_id) > 0:
                    print("Correct Set properly with empty well done & Improvement---------------------------")
                    query1 = """INSERT INTO model_results(review_header_id,result,well_done,improvement,additional_comments)VALUES (%s, %s, %s, %s, %s)"""
                    cur.execute(query1, [review_id, "Mismatched & Rejected", ", ".join([i for i in set(
                        well_done_id)]), ", ".join([i for i in set(improvement_id)]), ", ".join([i for i in set(
                        confirmlist1)])])
                    conn.commit()
                    # conn.close()
                    return jsonify({'additional_comment' : confirmlist1})
                elif len(well_done_id) > 0 and len(improvement_id) == 0:
                    print("Correct Set properly with empty Improvement---------------------------")
                    query1 = """INSERT INTO model_results(review_header_id,result,well_done,improvement,additional_comments)VALUES (%s, %s, %s, %s, %s)"""
                    cur.execute(query1, [review_id, "Mismatched & Rejected", ", ".join([i for i in set(well_done_id)]),
                                         " ", ", ".join([i for i in set(confirmlist1)])])
                    conn.commit()
                    # conn.close()
                    return jsonify({'additional_comment' : confirmlist1})
                elif len(well_done_id) == 0 and len(improvement_id) > 0:
                    print("Correct Set properly with empty well done---------------------------")
                    query1 = """INSERT INTO model_results(review_header_id,result,well_done,improvement,
                    additional_comments)VALUES (%s, %s, %s, %s, %s)"""
                    cur.execute(query1, [review_id, "Mismatched & Rejected", " ", ", ".join([i for i in set(
                        improvement_id)]), ", ".join([i for i in set(confirmlist1)])])
                    conn.commit()
                    # conn.close()
                    return jsonify({'additional_comment' : confirmlist1})
            query1 = """INSERT INTO model_results(review_header_id,result,well_done,improvement)VALUES (%s, %s, %s, %s)"""
            if len(well_done_id) > 0 and len(improvement_id) > 0:
                cur.execute(query1, [review_id, "Matched & Accepted", ", ".join([i for i in set(well_done_id)]), ", ".join([i for i in set(improvement_id)])])
                conn.commit()
            elif len(well_done_id) > 0 and len(improvement_id) == 0:
                cur.execute(query1, [review_id, "Matched & Accepted", ", ".join([i for i in set(well_done_id)]), " "])
                conn.commit()
            elif len(well_done_id) == 0 and len(improvement_id) > 0:
                cur.execute(query1, [review_id, "Matched & Accepted", " ", ", ".join([i for i in set(improvement_id)])])
                conn.commit()
            else:
                pass

        # conn.close()
        gc.disable()
        return jsonify({"Mismatched" : confirmlist1, "Well Done Area" : confirmlist2, "Improvement Area" : confirmlist3,
                        "well_done_ids" : well_done_id, "improvement_ids" : improvement_id})

if __name__ == "__main__":
    application.run(host = '0.0.0.0',port = '8000')



