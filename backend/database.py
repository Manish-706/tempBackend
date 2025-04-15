import pymysql
from config import MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DB, SSL_CA_PATH

def get_connection():
   return pymysql.connect(
       host=MYSQL_HOST,
       user=MYSQL_USER,
       password=MYSQL_PASSWORD,
       db=MYSQL_DB,
       ssl={'ca': SSL_CA_PATH},
       cursorclass=pymysql.cursors.DictCursor
   )
   return connection

# import pymysql
# from config import MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DB

# def get_connection():
#     connection = pymysql.connect(
#         host=MYSQL_HOST,
#         user=MYSQL_USER,
#         password=MYSQL_PASSWORD,
#         db=MYSQL_DB,
#         cursorclass=pymysql.cursors.DictCursor
#     )
#     return connection
