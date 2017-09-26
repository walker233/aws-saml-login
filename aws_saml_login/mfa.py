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

class Duo(object):
    def __init__(self):
        self.attributes = {}
        self.detectedDuo = False
        self.duoType = None

    def isFound(self,response):
        return self.detectedDuo or self.isFoundDuoScript(response) or self.isFoundDuoIframe(response)

    def isFoundDuoScript(self, response):
        duoMatch = re.search('Duo\.init\(({.*})\);', response.text, re.DOTALL)
        if duoMatch:
            self.attributes = literal_eval(duoMatch.group(1))
            self.detectedDuo = True
            self.duoType = "init"
            return True
        return False

        # duoMatch = re.search("Duo.init", response.text)
        #
        # return duoMatch is not None

    def isFoundDuoIframe(self, response):
        duoMatch = re.search('duo_iframe.*data-host', response.text, re.DOTALL)
        # duoMatch = re.search('<iframe id="duo_iframe"(.*)>.*</iframe>', response.text,re.DOTALL)
        if duoMatch:
            # self.attributes = ...
            self.detectedDuo = True
            self.duoType = "iframe"
            return True
        return False

    def getDuoAttributesFromFrame(self,duoFrameMatch):
        return {}

    def process(self,response,session):
        pass

    def getDuoAttributes(self):
        return self.attributes



    # idpForm = BeautifulSoup(response.text, 'html.parser')
    # # find the submit button name and value, as the name changes
    # for submittag in idpForm.find_all(re.compile('BUTTON|button')):
    #     name = submittag.get('name', '')
    #     value = submittag.contents[0]
    #     if submittag.get('type', '') == 'submit':
    #         data[name] = value
