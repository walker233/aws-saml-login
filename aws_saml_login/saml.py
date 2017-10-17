import re
import boto3
import codecs
from xml.etree import ElementTree
from bs4 import BeautifulSoup
import os
import configparser
import requests
from aws_saml_login import mfa

AWS_CREDENTIALS_PATH = '~/.aws/credentials'
OPENAM_SEARCH_STRING = 'XUI/#login/&'


def get_boto3_session(key_id, secret, session_token=None, region=None, profile=None):
    """
    get boto3 session for giving keys

    >>> get_boto3_session('keyid', 'secret', region='eu-central-1')
    Session(region_name='eu-central-1')

    >>> get_boto3_session(None, None, region='us-west-1')
    Session(region_name='us-west-1')

    """
    return boto3.session.Session(aws_access_key_id=key_id,
                                 aws_secret_access_key=secret,
                                 aws_session_token=session_token,
                                 region_name=region,
                                 profile_name=profile)


def write_aws_credentials(profile, key_id, secret, session_token=None):
    credentials_path = os.path.expanduser(AWS_CREDENTIALS_PATH)
    os.makedirs(os.path.dirname(credentials_path), exist_ok=True)
    config = configparser.ConfigParser()
    if os.path.exists(credentials_path):
        config.read(credentials_path)

    config[profile] = {}
    config[profile]['aws_access_key_id'] = key_id
    config[profile]['aws_secret_access_key'] = secret
    if session_token:
        # apparently the different AWS SDKs either use "session_token" or "security_token", so set both
        config[profile]['aws_session_token'] = session_token
        config[profile]['aws_security_token'] = session_token

    with open(credentials_path, 'w') as fd:
        config.write(fd)


def get_saml_response(html: str):
    """
    Parse SAMLResponse from Shibboleth page

    >>> get_saml_response('<input name="a"/>')

    >>> get_saml_response('<body xmlns="bla"><form><input name="SAMLResponse" value="eG1s"/></form></body>')
    'xml'
    """
    soup = BeautifulSoup(html, "html.parser")

    for elem in soup.find_all('input', attrs={'name': 'SAMLResponse'}):
        saml_base64 = elem.get('value')
        xml = codecs.decode(saml_base64.encode('ascii'), 'base64').decode('utf-8')
        return xml


def get_form_action(html: str):
    '''
    >>> get_form_action('<body><form action="test"></form></body>')
    'test'
    '''
    soup = BeautifulSoup(html, "html.parser")
    return soup.find('form').get('action')


def get_account_name(role_arn: str, account_names: dict):
    '''
    >>> get_account_name('arn:aws:iam::123:role/Admin', {'123': 'blub'})
    'blub'
    >>> get_account_name('arn:aws:iam::456:role/Admin', {'123': 'blub'})

    '''
    number = role_arn.split(':')[4]
    if account_names:
        return account_names.get(number)


def get_roles(saml_xml: str) -> list:
    """
    Extract SAML roles from SAML assertion XML

    >>> get_roles('''<xml xmlns="urn:oasis:names:tc:SAML:2.0:assertion"><Assertion>
    ... <Attribute FriendlyName="Role" Name="https://aws.amazon.com/SAML/Attributes/Role">
    ... <AttributeValue>arn:aws:iam::911:saml-provider/Shibboleth,arn:aws:iam::911:role/Shibboleth-User</AttributeValue>
    ... </Attribute>
    ... </Assertion></xml>''')
    [('arn:aws:iam::911:saml-provider/Shibboleth', 'arn:aws:iam::911:role/Shibboleth-User')]
    """
    tree = ElementTree.fromstring(saml_xml)

    assertion = tree.find('{urn:oasis:names:tc:SAML:2.0:assertion}Assertion')

    roles = []
    for attribute in assertion.findall('.//{urn:oasis:names:tc:SAML:2.0:assertion}Attribute[@Name]'):
        if attribute.attrib['Name'] == 'https://aws.amazon.com/SAML/Attributes/Role':
            for val in attribute.findall('{urn:oasis:names:tc:SAML:2.0:assertion}AttributeValue'):
                provider_arn, role_arn = val.text.split(',')
                roles.append((provider_arn, role_arn))
    return roles


def get_account_names(html: str) -> dict:
    '''
    Parse account names from AWS page

    >>> get_account_names('')
    {}

    >>> get_account_names('<div class="saml-account-name">Account: blub  (123) </div>')
    {'123': 'blub'}

    >>> get_account_names('<div class="saml-account-name">Account: blub  123) </div>')
    {}
    '''
    soup = BeautifulSoup(html, "html.parser")

    accounts = {}
    for elem in soup.find_all('div', attrs={'class': 'saml-account-name'}):
        try:
            name_number = elem.text.split(':', 1)[-1].strip().rstrip(')')
            name, number = name_number.rsplit('(', 1)
            name = name.strip()
            number = number.strip()
            accounts[number] = name
        except:
            # just skip account in case of parsing errors
            pass
    return accounts


class AuthenticationFailed(Exception):
    def __init__(self):
        pass


class AssumeRoleFailed(Exception):
    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return 'Assuming role failed: {}'.format(self.msg)


def authenticate(url, user, password, mfa_type=mfa.MfaNone):
    '''Authenticate against the provided Shibboleth Identity Provider.

    Supports Shibboleth or OpenAM.
    '''

    session = requests.Session()

    response = session.get(url)

    # Check if OpenAM is the IdP
    if OPENAM_SEARCH_STRING in response.url:
        server_info_url = response.url[:response.url.index(OPENAM_SEARCH_STRING)] + 'json/serverinfo/*'
        openam_url = response.url.replace(OPENAM_SEARCH_STRING, 'json/authenticate?', 1)

        # Get cookie name
        response = session.get(server_info_url)
        cookie_name = response.json()['cookieName']

        # Get login form
        response = session.post(openam_url)
        login_form = response.json()

        # Submit authentication credentials
        for item in login_form['callbacks']:
            if item['type'] == 'NameCallback':
                item['input'][0]['value'] = user
            if item['type'] == 'PasswordCallback':
                item['input'][0]['value'] = password

        response2 = session.post(openam_url, json=login_form)

        # Ask for second factor authentication, if necessary
        if 'stage' in response2.json():
            otp_form = response2.json()

            otp_code = input('Submit OTP code: ')
            for item in otp_form['callbacks']:
                if item['type'] == 'PasswordCallback':
                    item['input'][0]['value'] = otp_code

            response2 = session.post(openam_url, json=otp_form)

        if response2.status_code != 200:
            raise AuthenticationFailed()

        # Set cookie for SAML response
        session.cookies.set(cookie_name, response2.json()['tokenId'])

        response2 = session.get(response2.json()['successUrl'])
    else:
        # NOTE: parameters are hardcoded for Shibboleth IDP
        data = {'j_username': user, 'j_password': password}
        idpForm = BeautifulSoup(response.text, 'html.parser')
        #find the submit button name and value, as the name changes
        for submittag in idpForm.find_all(re.compile('BUTTON|button')):
            name = submittag.get('name', '')
            value = submittag.contents[0]
            if submittag.get('type', '') == 'submit':
                data[name] = value

        response2 = session.post(response.url, data=data)

    response2 = mfa_type(response2,session).process()

    saml_xml = get_saml_response(response2.text)
    if not saml_xml:
        raise AuthenticationFailed()

    url = get_form_action(response2.text)
    encoded_xml = codecs.encode(saml_xml.encode('utf-8'), 'base64')
    response3 = session.post(url, data={'SAMLResponse': encoded_xml})

    with open('aws_response','w') as f:
        f.write(response3.text)
    f.close()
    account_names = get_account_names(response3.text)

    roles = get_roles(saml_xml)

    roles = [(p_arn, r_arn, get_account_name(r_arn, account_names)) for p_arn, r_arn in roles]

    return saml_xml, roles


def assume_role(saml_xml, provider_arn, role_arn):
    saml_assertion = codecs.encode(saml_xml.encode('utf-8'), 'base64').decode('ascii').replace('\n', '')

    try:
        sts = boto3.client('sts')
        response_data = sts.assume_role_with_saml(RoleArn=role_arn,
                                                  PrincipalArn=provider_arn,
                                                  SAMLAssertion=saml_assertion)
    except Exception as e:
        raise AssumeRoleFailed(str(e))

    return tuple([response_data['Credentials'].get(x) for x in ('AccessKeyId', 'SecretAccessKey', 'SessionToken')])
