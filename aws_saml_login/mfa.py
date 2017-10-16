import re
from ast import literal_eval
from bs4 import BeautifulSoup

# Web Based implementation of Duo

# Options Hash:
# Duo.init({
#     iframe: "some_other_id",
#     host: "api-main.duo.test",
#     sig_request: "...",
#     post_action: "/auth",
#     post_argument: "resp"
#                     *});

# iframe based data- attributes:
# < iframe
# id = "duo_iframe"
# data-host = "api-main.duo.test"
# data-sig-request = "..."
# data-post-action = "/auth"
# data-post-argument = "resp"
#  >
#  < / iframe >

#Called this way: response2 = mfa_type(response2,session).process()

class MfaNone(object):
    def __init__(self, response, session):
        self.response = response

    def process(self):
        return self.response

class Duo(object):
#    def __init__(self, response, session):

    def host(self):
        return self.host or self.host = self.extract_host()

    def __init__(self, response, session):
        self.response = response
        self.session = session
        self.attributes = {}
        self.duoType = None

    def process(self):
        if not isFound():
            return self.response
        return self.response

    def isFound(response):
        return self.isFoundDuoScript(response) or self.isFoundDuoIframe(response)

    def isFoundDuoScript(self, response):
        duoMatch = re.search('Duo\.init\(({.*})\);', response.text, re.DOTALL)
        if duoMatch:
            self.storeDuoMatch(duoMatch, "init", literal_eval(duoMatch.group(1)))
        return duoMatch is not None

    def isFoundDuoIframe(self, response):
        duoMatch = re.search('(<iframe id="duo_iframe".*>.*</iframe>)', response.text,re.DOTALL)
        if duoMatch:
            self.storeDuoMatch(duoMatch, "iframe", self.getDuoAttributesFromFrame(self, duoMatch.group(1)))
        return duoMatch is not None

    def storeDuoMatch(self, match, duoType, attributes):
            self.duoType = duoType
            self.attributes = attributes

    def getDuoAttributesFromFrame(self,duoFrame):
        duoAttributes = {}
        duoSoup = BeautifulSoup(duoFrame, 'html.parser')
        for iframe in duoSoup.find_all(re.compile('iframe|IFRAME')):
            for key in iframe.attrs.keys():
                dataMatch = re.search('^data-(.*)', key)
                if dataMatch:
                    duoAttributes[dataMatch.group(1)] = iframe[key]
        return duoAttributes


    def getDuoAttributes(self):
        return self.attributes



    # idpForm = BeautifulSoup(response.text, 'html.parser')
    # # find the submit button name and value, as the name changes
    # for submittag in idpForm.find_all(re.compile('BUTTON|button')):
    #     name = submittag.get('name', '')
    #     value = submittag.contents[0]
    #     if submittag.get('type', '') == 'submit':
    #         data[name] = value
