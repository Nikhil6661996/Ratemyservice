"""DocString"""
try:
    # MAKE ALL THE MODULES AVAILABLE
    import sys
    import gc
    import pandas as pd
    from nltk.stem import WordNetLemmatizer
    from nltk.tokenize.punkt import PunktTrainer
    from nltk import sent_tokenize

    from flask import Flask, jsonify
    from rms.preprocesser import Cleaner
    from rms.config import DBConfigure
    from rms.blockwords import VulgurPrevent
    from rms.sentiment import SentimentAnalyzer
    from rms.collection import Collection

    import requests
    from apscheduler.schedulers.background import BackgroundScheduler


    TRAINER = PunktTrainer()
    TRAINER.INCLUDE_ALL_COLLOCS = True

    print("All the Modules are Successfully Imported")
except Exception as e:
    # PLEASE IMPORT THE MODULES FIRST
    print("Enable to import all the necessary Modules---", e)
    sys.exit()


def sensor(conn):
    df1 = pd.read_sql_query("SELECT * FROM review_headers",conn)

    df1 = df1[['id','nlp_status']]

    df1 = df1[df1.nlp_status == 0]

    qoservice,orating,qostaff,vfm,qoc,review,customer_effort,review_id = -1,-1,-1,-1,-1,'',4,-1

    if len(df1) > 0:
        review_id = df1.iloc[0].tolist()[0]

        df2 = pd.read_sql_query("SELECT * FROM review_details where review_header_id ='{}'".format(review_id), conn)

        df2 = df2[['rate_param_id','param_value']]

        record =df2.values.tolist()

        if len(record) == 0:
            record = [[2, '0'], [1, '0'], [3, '0'], [5, '0'], [4, '0'], [6, 'this is not a visible question hence should not be included in the calculation']]

        for item in record:
            ids = item[0]
            rating = item[1]
            if ids == 1:
                try:
                    qoservice = int(rating)
                except:
                    qoservice = 0
            elif ids == 2:
                try:
                    orating = int(rating)
                except:
                    orating = 0
            elif ids == 3:
                try:
                    qostaff = int(rating)
                except:
                    qostaff = 0
            elif ids == 4:
                try:
                    vfm = int(rating)
                except:
                    vfm = 0
            elif ids == 5:
                try:
                    qoc = int(rating)
                except:
                    qoc = 0
            elif ids == 6:
                try:
                    if rating == '':
                        review = 'this is not a visible question hence should not be included in the calculation'
                    else:
                        review = rating
                except:
                    review = ''
            else:
                pass
        
        return qoservice,orating,qostaff,vfm,qoc,review,customer_effort,review_id
    else:
        return qoservice,orating,qostaff,vfm,qoc,review,customer_effort,review_id
        

def get_api():
    API_ENDPOINT = "http://0.0.0.0:8000/rms"
    try:
        r = requests.get(API_ENDPOINT)
        print(r)
        print(r.json())
    except Exception as err:
        print("Get_API_Error------------------",err)
        
sched = BackgroundScheduler(daemon=True)
sched.add_job(get_api,'interval',seconds=30)
sched.start()


application = Flask(__name__)


@application.route("/rms", methods=['GET', 'POST'])
def home():
    gc.collect()
    conn = DBConfigure().db_conn()
    cur = conn.cursor()
    print("Connection created successfully")

    subdriver_tags = pd.read_sql_query("SELECT * FROM tags", conn)
    keyword_test = pd.read_sql_query("SELECT * FROM keywords", conn)
    regex_data = pd.read_sql_query("SELECT * FROM keywords WHERE keyword LIKE '%.+%';", conn)
    blockwords = pd.read_sql_query("SELECT * FROM blockwords", conn)
    review_phrase = pd.read_sql_query("SELECT * FROM review_phrase", conn)
    rate_params = pd.read_sql_query("SELECT * FROM rate_params", conn)
    stagwords = pd.read_sql_query("SELECT * FROM stagwords", conn)

    clf = SentimentAnalyzer(review_phrase).cl_dump()

    qoservice,orating,qostaff,vfm,qoc,review,customer_effort,review_id = sensor(conn)

    cur.execute("select * from model_results where review_header_id ='{}'".format(review_id))

    if len(cur.fetchall()) == 0:

        if (qoservice == -1) and (orating == -1) and (qostaff == -1) and (vfm == -1) and (qoc == -1):
            return jsonify("No Entry to Parse")
        else:
            try:
                if review.lower() == 'this is not a visible question hence should not be included in the calculation':
                    if orating != 0 and qoc != 0 and qoservice != 0 and qostaff != 0 and customer_effort != 0:
                        query1 = """INSERT INTO model_results(review_header_id, result, additional_comments)VALUES (%s, %s, %s)"""
                        cur.execute(query1, [review_id, "Accepted", "Accepted with no review text"])
                        cur.execute("Update review_headers SET nlp_status = 1 WHERE id = '{}'".format(review_id))

                        cur.close()
                        conn.close()
                        return jsonify({'Accepted': 'Accepted with no review text'})
                    else:
                        query1 = """INSERT INTO model_results(review_header_id,result, additional_comments)VALUES (%s, %s, %s)"""
                        cur.execute(query1, [review_id, "Accepted", "Accepted with no review text and incomplete ratings"])
                        cur.execute("Update review_headers SET nlp_status = 1 WHERE id = '{}'".format(review_id))

                        cur.close()
                        conn.close()
                        return jsonify({'Accepted': 'Accepted with no review text and incomplete ratings'})
                else:
                    review = " ".join([Cleaner().clean_text(text) for text in review.split(" ")])
                    word_lemma = WordNetLemmatizer()
                    review = " ".join([word_lemma.lemmatize(word, pos="v") if word not in ['is', 'was'] else word for word in review.split(" ")])

                    data = []
                    if len(sent_tokenize(review)) == 1:
                        for sent in review.split('and'):
                            sent = sent.strip()
                            if len([i for i in sent.split()]) > 50:
                                for j in sent.split('but'):
                                    data.append(j.strip())
                            else:
                                data.append(sent)
                    else:
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
                    if customer_effort < 1:
                        customer_effort = 3
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

                    drivers = Collection().db_search(cur, review, clf, subdriver_tags, keyword_test, review_phrase, rate_params)
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
                    for sentence in Collection().sent_part(review):
                        for item in Collection().key_search(sentence, subdriver_tags, regex_data, keyword_test, rate_params, stagwords):
                            if len(item) != 0:
                                shi = SentimentAnalyzer(review_phrase).polarise_this(sentence, clf2=clf)
                                item = [shi] + item
                                ritesh.append(item)

                    found_subdriver = [item[2] for item in ritesh]
                    for item in final:
                        if item[2] in found_subdriver:
                            found_subdriver.remove(str(item[2]))

                    for entry in ritesh:
                        for exist in found_subdriver:
                            if exist == entry[2]:
                                final.append(entry)


                    proied = VulgurPrevent(blockwords).profanity_filter(review)  # Check for block words in the Review

                    if "*" in proied:
                        query1 = """INSERT INTO model_results(review_header_id,result, additional_comments)VALUES (%s, %s, %s)"""
                        cur.execute(query1, [review_id, "Rejected Because of Blockwords", proied])
                        cur.execute("Update review_headers SET nlp_status = 1 WHERE id = '{}'".format(review_id))

                        cur.close()
                        conn.close()
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
                                aspect = {"Qualitycommunication": int(qoc), "Qualityservice": int(qoservice),
                                        "Qualitystaff": int(qostaff), "Valueformoney": int(vfm)}

                                if shi < 0.200000 and shi > -0.200000:
                                    shi = 0.000000

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

                                    if shi > 0.000000:
                                        confirmlist2.append(" ".join([str.capitalize(skey_name1)]))
                                        well_done_ids.append(skey_name)
                                    else:
                                        confirmlist3.append(" ".join([str.capitalize(skey_name1)]))
                                        improvement_ids.append(skey_name)
                    
                    if len(confirmlist1) == 0 and len(confirmlist2) == 0 and len(confirmlist3) == 0:
                        query1 = """INSERT INTO model_results(review_header_id,result,additional_comments)VALUES (%s, %s, %s)"""
                        cur.execute(query1, [review_id, "Accepted", "Rejected as review contain no meaning"])
                        cur.execute("Update review_headers SET nlp_status = 1 WHERE id = '{}'".format(review_id))
                        cur.close()
                        conn.close()
                        return jsonify({'additional_comment' : "Rejected as review contain no meaning"})
                    well_done_id, improvement_id = [], []
                    if len(well_done_ids) > 0 or len(improvement_ids) > 0:
                        if len(well_done_ids) > 0:
                            for text in well_done_ids:
                                well_done_id.append(str(subdriver_tags[subdriver_tags.tag == text].values.tolist()[0][0]))
                        if len(improvement_ids) > 0:
                            improvement_id = [str(subdriver_tags[subdriver_tags.tag == text].values.tolist()[0][0]) for text in
                                            improvement_ids]
                        if len(confirmlist1) > 0:
                            if len(well_done_id) > 0 and len(improvement_id) > 0:
                                query1 = """INSERT INTO model_results(review_header_id,result,well_done,improvement,additional_comments)
                                            VALUES (%s, %s, %s, %s, %s)"""
                                cur.execute(query1, [review_id, "Mismatched & Rejected", ", ".join([i for i in set(
                                    well_done_id)]), ", ".join([i for i in set(improvement_id)]), ", ".join([i for i in set(confirmlist1)])])
                                
                            elif len(well_done_id) > 0 and len(improvement_id) == 0:
                                query1 = """INSERT INTO model_results(review_header_id,result,well_done,improvement,additional_comments)
                                            VALUES (%s, %s, %s, %s, %s)"""
                                cur.execute(query1, [review_id, "Mismatched & Rejected", ", ".join([i for i in set(well_done_id)]),
                                                    " ", ", ".join([i for i in set(confirmlist1)])])
                                
                            elif len(well_done_id) == 0 and len(improvement_id) > 0:
                                query1 = """INSERT INTO model_results(review_header_id,result,well_done,improvement,
                                            additional_comments)VALUES (%s, %s, %s, %s, %s)"""
                                cur.execute(query1, [review_id, "Mismatched & Rejected", " ", ", ".join([i for i in set(
                                    improvement_id)]), ", ".join([i for i in set(confirmlist1)])])
                                
                            else:
                                pass
                        else:
                            query1 = """INSERT INTO model_results(review_header_id,result,well_done,improvement)
                                        VALUES (%s, %s, %s, %s)"""
                            if len(well_done_id) > 0 and len(improvement_id) > 0:
                                cur.execute(query1, [review_id, "Matched & Accepted", ", ".join([i for i in set(well_done_id)]),", ".join([i for i in set(improvement_id)])])
                                
                            elif len(well_done_id) > 0 and len(improvement_id) == 0:
                                cur.execute(query1, [review_id, "Matched & Accepted", ", ".join([i for i in set(well_done_id)]), " "])
                                
                            elif len(well_done_id) == 0 and len(improvement_id) > 0:
                                cur.execute(query1, [review_id, "Matched & Accepted", " ", ", ".join([i for i in set(improvement_id)])])
                                
                            else:
                                pass
                            
                        cur.execute("Update review_headers SET nlp_status = 1 WHERE id = '{}'".format(review_id))
                        
                        cur.close()
                        conn.close()
                        return jsonify({"Mismatched": confirmlist1, "Well Done Area": confirmlist2, "Improvement Area": confirmlist3,
                                        "well_done_ids": well_done_id, "improvement_ids": improvement_id})

            except Exception as err:
                if str(err).split(" (")[0] == '1062':
                    cur.execute("Update review_headers SET nlp_status = 1 WHERE id = '{}'".format(review_id))
                    cur.close()
                    conn.close()
                return jsonify("Error--------------"+str(err))
    else:
        cur.execute("Update review_headers SET nlp_status = 1 WHERE id = '{}'".format(review_id))
        cur.close()
        conn.close()
        return jsonify("Data Already Exist in the database")

if __name__ == "__main__":
    application.run(host='0.0.0.0', port='8000')

