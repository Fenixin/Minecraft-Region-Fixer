'''
Created on 16/09/2014

@author: Alejandro
'''

import ftplib
import datetime
from StringIO import StringIO
from util import query_yes_no


SERVER = 'regionfixer.no-ip.org'
USER = 'regionfixer_bugreporter'
PASSWORD = 'supersecretpassword'
BUGREPORTS_DIR = 'bugreports'
QUESTION_TEXT = 'Do you want to send an anonymous bug report to the region fixer ftp?'

class BugReporter(object):
    '''
    Reports a bug to a ftp
    '''

    def __init__(self, error, server=SERVER,
                 user=USER, password=PASSWORD):
        '''
        Constructor
        '''
        assert(isinstance(error, StringIO))
        error.seek(0)
        self.error_file_obj = error
        self.server = server
        self.user = user
        self.password = password

    def ask_and_send(self):
        if query_yes_no(QUESTION_TEXT):
            self.send()

    def send(self):
        try:
            s = ftplib.FTP(self.server, self.user,
                           self.password)

            s.cwd(BUGREPORTS_DIR)

            error_name = str(datetime.datetime.now())

            s.storlines("STOR " + error_name, self.error_file_obj)
            s.quit()
            print "Bug report uploaded successfully!"
            return True
        except Exception as e:
            print "Couldn't send the bug report!"
            return False
