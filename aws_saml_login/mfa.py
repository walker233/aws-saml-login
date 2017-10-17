
class MfaNone(object):
    def __init__(self, response, session):
        self.response = response

    def process(self):
        return self.response