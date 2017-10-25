import re
from bs4 import BeautifulSoup
import duo_client
import pickle

class MfaNone(object):

    def __init__(self, response, session):
        self.response = response

    def process(self):
        return self.response

    @staticmethod
    def detect(response,session):
        return MfaNone(response,session)

class Duo(object):

    api_endpoint = "/frame/web/v1/auth?"

    @staticmethod
    def detect(response,session):
        attributes = DuoScript.findAttributes(response)
        if ( len(attributes) > 0 ):
            return DuoScript(response, session, attributes)

        attributes = DuoIframe.findAttributes(response)
        if (len(attributes) > 0):
            return DuoIframe(response, session, attributes)

        return MfaNone(response, session)

    def parseSigRequest(self):
        try:
            if (self.sig_request.index('ERR|') is 0 ):
                raise ValueError('Signature returned error state' + self.sig_request)
        except ValueError as err:
            pass

        duoSig, appSig = self.sig_request.split(':')
        return duoSig, appSig

class DuoScript(Duo):
    @staticmethod
    def findAttributes(response):
        attributes = {}
        print( len(attributes) > 0 )
        duoMatch = re.search('Duo\.init\(.*({.*}).*\);', response.text, re.DOTALL)
        if duoMatch:
            attributes = DuoScript.getDuoAttributesFromScript( duoMatch.group(1) )
        return attributes

    @staticmethod
    def getDuoAttributesFromScript(matched):
        attributes = {}
        for(key,value) in re.findall(r'[\'"]?([\w_]+)[\'"]?:\s*[\'"]([^\'"]+)[\'"],?\s', matched, re.DOTALL):
            attributes[key] = value
        return attributes

    def __init__(self, response,session, attributes):
        self.response = response
        self.session = session
        print(attributes)
        self.host = attributes['host']
        self.sig_request = attributes['sig_request']
        self.post_action = attributes['post_action']

        if ('post_arguments' in attributes):
            self.post_argument = attributes['post_argument']
        if ('iframe' in attributes):
            self.iframe = attributes['iframe']

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

        self.host = attributes['host']
        self.sig_request = attributes['sig_request']
        self.post_action = attributes['post_action']

        if ('post_arguments' in attributes):
            self.post_argument = attributes['post_argument']
        if ('iframe' in attributes):
            self.iframe = attributes['iframe']

    def process(self):
        return self.response