'''
Database Connection and Configuration for Ratemyservice NLP
'''
# Necessary Imports
import mysql.connector as mysqldb

class DBConfigure():
    ''' Constructor Initialization '''
    def __init__(self):
        self.mysqldb = mysqldb

    def __str__(self):
        return self.__class__.__name__

    def db_conn(self):
        ''' DataBase Connection '''
        try:
            connection = self.mysqldb.connect(host="localhost", port=3306, database="ratemyservice_dev", user="root", password="", autocommit=True)
        except Exception as err:
            connection = self.mysqldb.connect(host="localhost", port=3306, database="ratemyservice_dev", user="root", password="", autocommit=True)
            print(err)
        return connection
        