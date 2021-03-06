"""Script to create a pool of use cases from actual users."""
import datetime
import json
import os
import re
import sys
from urllib import parse

from google.protobuf import json_format
import pymongo
import requests

from bob_emploi.frontend import privacy

_DB = pymongo.MongoClient(os.getenv('MONGO_URL', 'mongodb://localhost/test'))\
    .get_default_database()

# A Slack WebHook URL to send final reports to. Defined in the Incoming
# WebHooks of https://bayesimpact.slack.com/apps/A0F7XDUAZ-incoming-webhooks
_SLACK_CREATE_POOL_URL = os.getenv('SLACK_CREATE_POOL_URL')

# The base URL to use as the prefix of all links to the website. E.g. in dev,
# you should use http://localhost:3000.
_BASE_URL = os.getenv('BASE_URL', 'https://www.bob-emploi.fr')

_YESTERDAY = (datetime.date.today() + datetime.timedelta(days=-1)).strftime('%Y-%m-%d')
_DEFAULT_USERS_FILTER = {
    'profile.email': {'$not': re.compile('@example.com|@bayes')},
    'registeredAt': {'$gt': _YESTERDAY, '$lt': '%sT24' % _YESTERDAY},
    'projects.createdAt': {'$exists': True},
    'projects.isIncomplete': {'$ne': True},
}


def main(pool_name=_YESTERDAY, users_json_filters=None, limit=20):
    """Create a pool of use cases and store them in MongoDB."""
    users_filters = json.loads(users_json_filters) if users_json_filters else _DEFAULT_USERS_FILTER
    user_iterator = _DB.user.find(users_filters).limit(int(limit))
    for user_index, user_dict in enumerate(user_iterator):
        use_case_proto = privacy.user_to_use_case(user_dict, pool_name, user_index)
        use_case = json_format.MessageToDict(use_case_proto)
        use_case['_id'] = use_case.pop('useCaseId')
        try:
            _DB.use_case.insert_one(use_case)
        except pymongo.errors.DuplicateKeyError:
            _DB.use_case.replace_one({'_id': use_case['_id']}, use_case)

    if _SLACK_CREATE_POOL_URL:
        requests.post(_SLACK_CREATE_POOL_URL, json={
            'text': 'A new use cases pool is ready for evaluation: <%s|%s>' % (
                '%s/eval?poolName=%s' % (_BASE_URL, parse.quote(pool_name)), pool_name)})


if __name__ == '__main__':
    main(*sys.argv[1:])
