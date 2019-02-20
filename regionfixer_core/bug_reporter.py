'''
Created on 16/09/2014

@author: Alejandro
'''

import sys
import ftplib
import datetime
from io import StringIO
from .util import query_yes_no, get_str_from_traceback


SERVER = 'regionfixer.no-ip.org'
USER = 'regionfixer_bugreporter'
PASSWORD = 'supersecretpassword'
BUGREPORTS_DIR = 'bugreports'


class BugReporter(object):
    '''
    Class to report bugs to region fixer ftp.

    You can init it without arguments and it will extract the traceback
    directly from sys.exc_info(). The traceback will be formated and
    uploaded as a text file.
    Or you can init it using an error string (error_str). The string
    will be uploaded as a text file.
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
        ''' Return a file obj from a traceback object. '''
        f = StringIO(get_str_from_traceback(ty, value, tb))
        f.seek(0)
        return f

    def _get_fileobj_from_str(self, error_str):
        ''' Return a file object from a string. '''
        f = StringIO(error_str)
        f.seek(0)
        return f

    @property
    def error_str(self):
        ''' Return the string that is currently ready for upload. '''
        self.error_file_obj.seek(0)
        s = self.error_file_obj.read()
        self.error_file_obj.seek(0)
        return s

    @property
    def exception_str(self):
        ''' Return the exception caused by uploading the file. '''
        return self._exception.message

    def ask_and_send(self, question_text):
        ''' Query the user yes/no to send the file and send it. '''
        if query_yes_no(question_text):
            return self.send()

    def send(self):
        ''' Send the file to the ftp.

        If an exception is thrown, you can retrieve it at
        exception_str.
        '''
        try:
            s = ftplib.FTP(self.server, self.user,
                           self.password)

            s.cwd(BUGREPORTS_DIR)

            error_name = str(datetime.datetime.now())

            s.storlines("STOR " + error_name, self.error_file_obj)
            s.quit()
            return True
        except Exception as e:
            # TODO: prints shouldn't be here!
            print("Couldn't send the bug report!")
            self._exception = e
            print(e)
            return False
