import pymysql
from config import MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DB, SSL_CA_PATH

try:
    connection = pymysql.connect(
        host=MYSQL_HOST,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        db=MYSQL_DB,
        ssl={'ca': SSL_CA_PATH}
    )
    print("✅ Connected successfully!")
except Exception as e:
    print(f"❌ Connection failed: {e}")