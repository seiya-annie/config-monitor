#coding=utf-8
import pymysql
import configparser

class mysql_opt():

    def __init__(self):
        config        = configparser.ConfigParser()
        config.read("db.ini")

        self.host = config.get("DB_IP","db")
        self.user = config.get("USER","user")
        self.pwd  = config.get("PASSWORD","password")
        # self.pwd = ''
        self.db   = config.get("DB", "database")
        self._conn = self.GetConnect()
        if(self._conn):
            self._cur = self._conn.cursor()

    #connection
    def GetConnect(self):
        conn = False
        try:
            conn = pymysql.connect(
                self.host,
                self.user,
                self.pwd,
                self.db
            )
        except Exception as err:
            print("connect to db fail, %s" % err)
        else:
            return conn
 
 
    #execute sql
    def ExecQuery(self,sql):
        res = ""
        try:
            self._cur.execute(sql)
            res = self._cur.fetchall()
        except Exception as err:
            print("execute sql fail, %s" % err)
            return err
        else:
            return res
 
 

    #get connectinfo
    def GetConnectInfo(self):
        print( "connection info��" )
        print( "server:%s , user:%s , db:%s " % (self.host,self.user,self.db))
 
 
 
    #close connection
    def Close(self):
        if(self._conn):
            try:
                if(type(self._cur)=='object'):
                    self._cur.close()
                if(type(self._conn)=='object'):
                    self._conn.close()
            except:
                raise("close fail, %s,%s" % (type(self._cur), type(self._conn)))  
 

