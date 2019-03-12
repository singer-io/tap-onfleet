
#
# Module dependencies.
#

from datetime import datetime, timedelta
from requests.auth import HTTPBasicAuth
from singer import utils
import backoff
import requests
import logging
import time
import sys


logger = logging.getLogger()


""" Simple wrapper for Onfleet. """
class Onfleet(object):

  def __init__(self, start_date=None, user_agent=None, api_key=None, quota_limit=50):
    self.user_agent = user_agent
    self.start_date = start_date
    self.quota_limit = quota_limit
    self.api_key = api_key
    self.uri = "https://onfleet.com/api/v2/"


  def check_rate_limit(self, rate_limit_remaining=None, rate_limit_limit=None):
    # print(float(rate_limit_remaining) / float(rate_limit_limit) * 100)
    # print(type(rate_limit_remaining))
    # print(rate_limit_limit)
    # print(type(rate_limit_limit))

    if float(rate_limit_remaining) / float(rate_limit_limit) * 100 < self.quota_limit:
      time.sleep(2000)


  @backoff.on_exception(backoff.expo,
                        requests.exceptions.RequestException)
  def _get(self, path, **kwargs):
    uri = "{uri}{path}".format(uri=self.uri, path=path)
    logger.info("GET request to {uri}".format(uri=uri))
    response = requests.get(uri, auth=HTTPBasicAuth(self.api_key, ''))
    response.raise_for_status()
    self.check_rate_limit(response.headers.get('X-RateLimit-Remaining'), response.headers.get('X-RateLimit-Limit'))
    return response.json()


  # 
  # Methods to retrieve data per stream/resource.
  # 

  def administrators(self, column_name=None, bookmark=None):
    return self._get("admins")


  def hubs(self, column_name=None, bookmark=None):
    return self._get("hubs")


  def organizations(self, column_name=None, bookmark=None):
    return self._get("organization")


  def tasks(self, column_name=None, bookmark=None):
    return self._get("tasks")


  def teams(self, column_name=None, bookmark=None):
    return self._get("teams")


  def workers(self, column_name=None, bookmark=None):
    return self._get("workers")




