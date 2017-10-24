import pytest
from unittest.mock import MagicMock
import datetime
from dateutil.tz import tzutc
from aws_saml_login.saml import authenticate, assume_role, write_aws_credentials, get_boto3_session
from aws_saml_login.saml import AssumeRoleFailed
import tempfile
import os
import configparser
import requests
from aws_saml_login import mfa


def test_assume_role(monkeypatch):
    sts = MagicMock()
    sts.assume_role_with_saml.return_value = {
        'Audience': 'https://signin.aws.amazon.com/saml',
        'Credentials': {
            'AccessKeyId': 'abcdef',
            'Expiration': datetime.datetime(2015, 12, 1, 14, 37, 38, tzinfo=tzutc()),
            'SecretAccessKey': 'GEHEIM',
            'SessionToken': 'toktok'
        },
        'Issuer': 'https://idp.example.org/shibboleth'
    }
    monkeypatch.setattr('boto3.client', MagicMock(return_value=sts))

    assert ('abcdef', 'GEHEIM', 'toktok') == assume_role('saml_xml', 'provider_arn', 'role_arn')


def test_assume_role_except(monkeypatch):
    sts = MagicMock()
    sts.assume_role_with_saml.side_effect = Exception('anything is wrong')
    monkeypatch.setattr('boto3.client', MagicMock(return_value=sts))

    with pytest.raises(AssumeRoleFailed) as excinfo:
        assume_role('saml_xml', 'provider_arn', 'role_arn')
    assert str(excinfo.value) == 'Assuming role failed: anything is wrong'


def test_write_aws_credentials(monkeypatch):
    temp_credentials_path = tempfile.mkstemp()[1]
    monkeypatch.setattr('aws_saml_login.saml.AWS_CREDENTIALS_PATH', temp_credentials_path)
    write_aws_credentials('pytest-dummy', 'dummy-key-id', 'very-secret', 'session-token')
    write_aws_credentials('pytest2-dummy', 'asdfasdf', '0123456789')
    config = configparser.ConfigParser()
    if os.path.exists(temp_credentials_path):
        config.read(temp_credentials_path)
        os.remove(temp_credentials_path)
    assert 'dummy-key-id' == config['pytest-dummy']['aws_access_key_id']
    assert 'very-secret' == config['pytest-dummy']['aws_secret_access_key']
    assert 'session-token' == config['pytest-dummy']['aws_session_token']

    assert 'asdfasdf' == config['pytest2-dummy']['aws_access_key_id']
    assert '0123456789' == config['pytest2-dummy']['aws_secret_access_key']
    assert 'did not exists' == config['pytest2-dummy'].get('aws_session_token', 'did not exists')


def test_authenticate(monkeypatch):
    pass

class FakeResponse:
    def __init__(self,fileName):
        f = open(fileName)
        self.text = f.read()

    def len(self):
        return len(self.text)

# @pytest.mark.skip(reason="Don't care right now.")
def test_authenticate_takes_mfa_argument(monkeypatch):
    url = 'https://idp.example.com/idp/profile/SAML2/Unsolicited/SSO?providerId=urn:amazon:webservices'
    def mockgetresponse(session, url):
        response = MagicMock()
        fr = FakeResponse('tests/mock_idpLogin.html')
        fr.url = url
        return fr
    def mockpostresponse(session, url, data):
        fr = FakeResponse('tests/mock_saml_sanitized.html')
        return fr

    monkeypatch.setattr(requests.Session, 'get', mockgetresponse)
    monkeypatch.setattr(requests.Session, 'post', mockpostresponse)
    authenticate(url,"user","password")
    authenticate(url,"user","password", mfa.MfaNone)
    authenticate(url,"user","password", mfa.Duo)

@pytest.fixture
def fSession():
    return requests.Session()

def test_duo_selected_response_has_no_duoInit(monkeypatch):
    fr = FakeResponse('tests/mock_noDuoInitScript.html')
    duo = mfa.Duo.detect(fr,fSession)
    assert isinstance(duo,mfa.MfaNone)
    response2 = duo.process()
    assert len(response2.text) == len(fr.text)


def test_duo_selected_response_has_duo_script(monkeypatch):
    fr = FakeResponse('tests/mock_duoInitScript.html')
    duo = mfa.Duo.detect(fr,fSession)
    assert isinstance(duo,mfa.DuoScript)
    response2 = duo.process()
    attributes = mfa.DuoScript.findAttributes(fr)
    print(attributes)
    assert 'iframe' in attributes
    assert 'host' in attributes
    assert 'sig_request' in attributes
    assert 'post_action' in attributes
    assert 'post_argument' in attributes

def test_duo_selected_response_has_duo_iframe(monkeypatch):
    fr = FakeResponse('tests/mock_duoIframeData.html')
    duo = mfa.Duo.detect(fr,fSession)
    assert isinstance(duo,mfa.DuoIframe)
    response2 = duo.process()
    attributes = mfa.DuoIframe.findAttributes(fr)
    assert 'iframe' in attributes
    assert 'host' in attributes
    assert 'sig_request' in attributes
    assert 'post_action' in attributes
    assert 'post_argument' in attributes

def test_duo_sigParse(monkeypatch):
    fr = FakeResponse('tests/mock_duoIframeWithData.html')
    duo = mfa.Duo.detect(fr,fSession)
    duoSig = "TX|d3N3aGVlbGVyfERJV0lPUjdGSVdQV0NDSTZXQkVNfDE1MDg3OTg3MTE=|fee6c90bb13e60851690325255a70b2ced1507b3"
    appSig = "APP|d3N3aGVlbGVyfERJV0lPUjdGSVdQV0NDSTZXQkVNfDE1MDg4MDIwMTE=|b3f3cd3e90ecd7dd5495cec8a6984539787e5513"

    dSig, aSig = duo.parseSigRequest()
    assert dSig == duoSig
    assert aSig == appSig