import pytest
from unittest.mock import MagicMock
import datetime
from dateutil.tz import tzutc
from aws_saml_login.saml import authenticate, assume_role, write_aws_credentials, get_boto3_session
from aws_saml_login.saml import AssumeRoleFailed
from aws_saml_login.mfa import Duo
import tempfile
import os
import configparser


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


@pytest.fixture
def duo():
    return Duo()


def test_found_duo_is_found_with_initScript(duo,monkeypatch):
    response = FakeResponse('tests/mock_duoInitScript.html')
    assert True == duo.isFound(response)


def test_not_found_duo_is_found_with_initScript(duo,monkeypatch):
    response = FakeResponse('tests/mock_noDuoInitScript.html')
    assert False == duo.isFound(response)


def test_found_duo_is_found_with_iframe_data(duo,monkeypatch):
    response = FakeResponse('tests/mock_duoIframeData.html')
    assert True == duo.isFound(response)

def test_not_found_duo_is_found_with_iframe_data(duo,monkeypatch):
    response = FakeResponse('tests/mock_noDuoInitScript.html')
    assert False == duo.isFound(response)


def test_duo_get_duo_attributes_fromInit(duo,monkeypatch):
    expectedAttributes = {
        'host': 'api-082f11a6.duosecurity.com',
        'sig_request': 'TX|d3N3aGVlbGVyfERJV0lPUjdGSVdQV0NDSTZXQkVNfDE0ODUyOTU2MTQ=|46d3d2c036d08418cb164bdeab226109372ae996:APP|d3N3aGVlbGVyfERJV0lPUjdGSVdQV0NDSTZXQkVNfDE0ODUyOTg5MTQ=|1b197044e7b88213ba2325ce88da4034970ad30d',
        'post_argument': 'signedDuoResponse'
    }
    response = FakeResponse('tests/mock_duoInitScript.html')
    duo.isFound(response)

    assert duo.getDuoAttributes() == expectedAttributes

def test_duo_get_duo_attributes_fromIframe(duo, monkeypatch):
    expectedAttributes = {
        'host': 'api-082f11a6.duosecurity.com',
        'sig-request': 'TX|d3N3aGVlbGVyfERJV0lPUjdGSVdQV0NDSTZXQkVNfDE1MDYzODA4NjY=|6e120783743d8172d53d2d50411749d21a585e8e:APP|d3N3aGVlbGVyfERJV0lPUjdGSVdQV0NDSTZXQkVNfDE1MDYzODQxNjY=|abe510d7b3683c093f0e3e9dfb2eebb0503b1a5e',
        'post-action': '/idp/profile/SAML2/Unsolicited/SSO?execution=e1s2'
    }
    response = FakeResponse('tests/mock_duoIframeData.html')
    duo.isFound(response)
    assert duo.getDuoAttributes() == expectedAttributes



# def test_duo_process_from_initScript(duo,monkeypatch):
#     assert False == True
