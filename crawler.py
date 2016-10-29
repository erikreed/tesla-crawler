import argparse
import requests
import logging
import pandas as pd
import time
from pprint import pformat


logging.basicConfig()
logger = logging.getLogger('tesla-crawler')
logger.setLevel(logging.INFO)

URL = 'https://www.tesla.com/cpo_tool/ajax?exteriors=&model=MODEL_S&priceRange=0%2C150000' \
      '&metroId=3&sort=featured%7Casc&titleStatus=used&country=US'
SLEEP_TIME = 60


def filter_p85_autopilot(df):
    return df[df['isAutopilot'] & df['Badge'].isin(['P85', 'P85+'])]


class TeslaCrawler:
    def __init__(self, slack_client, filter_criteria=lambda df: df):
        self.cars_seen = set()
        self.slack_client = slack_client
        self.filter_criteria = filter_criteria

    def check(self):
        cars = pd.DataFrame(requests.get(URL).json())
        logger.info('Fetched %d cars', len(cars))

        filtered_cars = self.filter_criteria(cars)
        logger.info('Cars matching criteria: %d', len(filtered_cars))

        for _, c in filtered_cars[~filtered_cars['Vin'].isin(self.cars_seen)].iterrows():
            logger.info('Spotted new %s', c)
            if self.slack_client:
                self.slack_client.send_message('Spotted new: ```%s```' % pformat(c))

        new_cars = set(cars['Vin']).difference(self.cars_seen)
        if len(new_cars):
            logger.info('Added %d new vins', len(new_cars))
            if self.slack_client:
                self.slack_client.send_message('Added %d new VINs.' % len(new_cars))

        self.cars_seen.update(cars['Vin'])
        logger.info('VINs seen: %d', len(self.cars_seen))


class TeslaSlackClient:
    def __init__(self, token, channel, username):
        from slackclient import SlackClient

        self.client = SlackClient(token)
        self.channel = channel
        self.username = username
        logger.debug('Initialized Slack client with username %s, channel %s', self.username, self.channel)

    def send_message(self, text):
        logger.debug(self.client.api_call(
            'chat.postMessage',
            channel=self.channel,
            text=text,
            username=self.username,
        ))


def main():
    parser = argparse.ArgumentParser(description='Tesla CPO crawler and slack client')
    parser.add_argument('--slack-token', help='Slack API token. If not set, do not enable Slack client.')
    parser.add_argument('--slack-username', help='Slack username to post as')
    parser.add_argument('--slack-channel', help='Slack channel to VINs to')

    args = parser.parse_args()
    if args.slack_token:
        assert args.slack_username and args.slack_channel
        slack_client = TeslaSlackClient(token=args.slack_token, channel=args.slack_channel, username=args.slack_username)
    else:
        logger.info('Slack client not enabled')
        slack_client = None

    crawler = TeslaCrawler(slack_client=slack_client, filter_criteria=filter_p85_autopilot)
    while True:
        crawler.check()
        logger.debug('Sleeping %d seconds...', SLEEP_TIME)
        time.sleep(SLEEP_TIME)

if __name__ == '__main__':
    main()
