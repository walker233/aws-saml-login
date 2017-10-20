import re
from bs4 import BeautifulSoup

class MfaNone(object):

    def __init__(self, response, session):
        self.response = response

    def process(self):
        return self.response

    @staticmethod
    def detect(response,session):
        return MfaNone(response,session)

class Duo(object):

    @staticmethod
    def detect(response,session):
        attributes = DuoScript.findAttributes(response)
        if ( len(attributes) > 0 ):
            return DuoScript(response, session, attributes)

        attributes = DuoIframe.findAttributes(response)
        if (len(attributes) > 0):
            return DuoIframe(response, session, attributes)

        return MfaNone(response, session)

class DuoScript(Duo):
    @staticmethod
    def findAttributes(response):
        attributes = {}
        print( len(attributes) > 0 )
        duoMatch = re.search('Duo\.init\(.*({.*}).*\);', response.text, re.DOTALL)
        if duoMatch:
            attributes = duoMatch.group(1)
        return attributes

    def __init__(self, response,session, attributes):
        self.response = response
        self.session = session
        self.attributes = attributes

    def process(self):
        return self.response

class DuoIframe(Duo):
    @staticmethod
    def findAttributes(response):
        attributes = {}
        duoMatch = re.search('(<iframe .*"duo_iframe".*>.*</iframe>)',
                             response.text, re.DOTALL)
        if duoMatch:
            attributes = DuoIframe.getDuoAttributesFromFrameElement(duoMatch.group(1))
        return attributes

    @staticmethod
    def getDuoAttributesFromFrameElement(match):
        attributes = {}
        for iframe in BeautifulSoup(match, 'html.parser'):
            for key in iframe.attrs.keys():
                newkey = key.replace('data-','')
                newkey = newkey.replace('-','_')
                newkey = newkey.replace('id','iframe')
                attributes[newkey] = iframe.attrs[key]
        return attributes


    def __init__(self,response, session, attributes):
        self.response = response
        self.session = session

    def process(self):
        return self.response