'''
Created on 16/09/2014

@author: Alejandro
'''

import traceback
import sys
import ftplib
import datetime
from StringIO import StringIO
from util import query_yes_no


SERVER = '192.168.1.3'
USER = 'regionfixer_bugreporter'
PASSWORD = 'supersecretpassword'
BUGREPORTS_DIR = 'bugreports'


class BugReporter(object):
    '''
    Reports a bug to the regionfixer ftp
    '''

    def __init__(self, error_str=None, server=SERVER,
                 user=USER, password=PASSWORD):
        '''
        Constructor
        '''
        if error_str:
            self.error_file_obj = self._get_fileobj_from_str(error_str)
        else:
            (ty, value, tb) = sys.exc_info()
            self.error_file_obj = self._get_fileobj_from_tb(ty, value, tb)
        self.server = server
        self.user = user
        self.password = password
        
        self._exception = None

    def _get_fileobj_from_tb(self, ty, value, tb):
        f = StringIO("")
        f.write(str(ty) + "\n")
        f.write(str(value) + "\n")
        traceback.print_tb(tb, None, f)
        f.seek(0)
        return f

    def _get_fileobj_from_str(self, error_str):
        bug_report = str
        f = StringIO(bug_report)
        f.seek(0)
        return f

    @property
    def error_str(self):
        self.error_file_obj.seek(0)
        s = self.error_file_obj.read()
        self.error_file_obj.seek(0)
        return s

    #property
    def exception(self):
        return self._exception

    def ask_and_send(self, question_text):
        if query_yes_no(question_text):
            return self.send()

    def send(self):
        try:
            s = ftplib.FTP(self.server, self.user,
                           self.password)

            s.cwd(BUGREPORTS_DIR)

            error_name = str(datetime.datetime.now())

            s.storlines("STOR " + error_name, self.error_file_obj)
            s.quit()
            return True
        except Exception as e:
            self.exception = e
            return False
