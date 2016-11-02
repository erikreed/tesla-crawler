import argparse
import requests
import logging
import pandas as pd
import time


logging.basicConfig()
logger = logging.getLogger('tesla-crawler')
logger.setLevel(logging.INFO)

METRO_ID = None  # 3 corresponds to SF

URL = 'https://www.tesla.com/cpo_tool/ajax?exteriors=&model=MODEL_S&priceRange=0%2C150000' \
              '&sort=featured%7Casc&titleStatus=used&country=US'
if METRO_ID is not None:
    URL += '&metroId=%d' % METRO_ID

SLEEP_TIME = 180


def filter_p85_autopilot(df):
    return df[df['isAutopilot'] & df['Badge'].isin(['P85', 'P85+'])]


class TeslaCrawler:
    def __init__(self, slack_client, filter_criteria=lambda df: df):
        self.cars_seen = pd.DataFrame()
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
                self.slack_client.send_message('Spotted new: ```%s```' % str(c))

        new_cars = cars if self.cars_seen.empty else cars[~cars['Vin'].isin(self.cars_seen['Vin'])]
        if len(new_cars):
            msg = 'Added %d new vins: ```%s```' % (len(new_cars), cars.groupby(['Badge', 'isAutopilot']).size().to_string())
            logger.info(msg)
            if self.slack_client:
                self.slack_client.send_message(msg)

        self.cars_seen = cars if self.cars_seen.empty else self.cars_seen.merge(cars, on='Vin', copy=False)
        logger.info('VINs seen: %d', len(self.cars_seen))


class TeslaSlackClient:
    def __init__(self, webhook):
        self.webhook = webhook
        logger.debug('Initialized Slack client with webhook URL: %s', webhook)

    def send_message(self, text):
        r = requests.post(
            url=self.webhook,
            json={'text': text},
        )
        assert r.status_code == 200


def main():
    parser = argparse.ArgumentParser(description='Tesla CPO crawler and slack client')
    parser.add_argument('--slack-webhook', help='Slack webhook URL.')

    args = parser.parse_args()
    if args.slack_webhook:
        slack_client = TeslaSlackClient(webhook=args.slack_webhook)
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
