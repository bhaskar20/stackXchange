from urllib.parse import parse_qsl

import requests
from django.conf import settings
from toolz.dicttoolz import dissoc

from stackXchange.constants import (
    STACK_EXCHANGE_ACCESS_TOKEN_URI,
    STACK_EXCHANGE_API_USER_ACESS_TOKEN,
    STACK_EXCHANGE_API_USER_ASSOCCIATION,
)
from stackXchange.exceptions import BadStatusCode
from stackXchange.utils.functional import apply_key_map


def get_request(url):
    return requests.get(url)


def post_request(url, data={}):
    return requests.post(url, data)


def parse_query(query_str):
    return dict(parse_qsl(query_str))


def validate_status_code(response):
    if response.status_code != 200:
        raise BadStatusCode(
            'Received status code {0}'.format(response.status_code)
        )


class StackOverflowOauth:

    def __init__(self,
                 client_id=settings.STACK_EXCHANGE['CLIENT_ID'],
                 key=settings.STACK_EXCHANGE['KEY'],
                 secret=settings.STACK_EXCHANGE['SECRET'],
                 redirect_uri=settings.STACK_EXCHANGE['REDIRECT_URI']):
        self.client_id = client_id
        self.key = key
        self.secret = secret
        self.redirect_uri = redirect_uri

    def get_user_from_code(self, code):
        access_token = self.get_access_token_from_code(code)
        account_id = self.get_account_id_from_access_token(access_token)
        user_data = self.get_user_from_account_id(account_id)
        return {
            'access_token': access_token,
            'account_id': account_id,
            'user_data': user_data
        }

    def get_access_token_from_code(self, code):
        data = {
            'client_id': self.client_id,
            'client_secret': self.secret,
            'code': code,
            'redirect_uri': self.redirect_uri,
        }
        response = post_request(STACK_EXCHANGE_ACCESS_TOKEN_URI, data)
        validate_status_code(response)
        user_data = response.text
        return parse_query(user_data)['access_token']

    @staticmethod
    def get_account_id_from_access_token(access_token):
        url = STACK_EXCHANGE_API_USER_ACESS_TOKEN.format(access_token=access_token)
        response = get_request(url)
        validate_status_code(response)
        user_data = response.json()
        return user_data['items'][0]['account_id']

    def get_user_from_account_id(self, account_id):
        url = STACK_EXCHANGE_API_USER_ASSOCCIATION.format(user_id=account_id)
        response = get_request(url)
        validate_status_code(response)
        user_data = response.json()
        return self._get_user_site_details(user_data)

    @staticmethod
    def _get_user_site_details(user_data):
        user = []
        allowed_keys = {'user_id',  'site_url', 'site_name'}
        remapped_keys = {'user_id': 'site_user_id'}
        keys_to_dissoc = set(user_data['items'][0].keys()) - allowed_keys
        for site in user_data['items']:
            filtered_data = dissoc(site, *keys_to_dissoc)
            remapped_data = apply_key_map(remapped_keys, filtered_data)
            user.append(remapped_data)
        return user
