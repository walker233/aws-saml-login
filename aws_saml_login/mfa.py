import re

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
        if DuoScript.isFound(response):
            return DuoScript(response,session)
        return MfaNone(response,session)


class DuoScript(Duo):
    @staticmethod
    def isFound(response):
        duoMatch = re.search('Duo\.init\(({.*})\);', response.text, re.DOTALL)
        return duoMatch is not None

    def __init__(self, response,session):
        self.response = response
        self.session = session

    def process(self):
        return self.response
