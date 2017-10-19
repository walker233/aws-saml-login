
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
        return MfaNone(response,session)


class DuoScript(Duo):
    pass