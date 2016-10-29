# Tesla Crawler CPO w/ Slack Client
This crawls the official Tesla CPO (certified pre-owned) inventory based on some criteria and posts the results to a Slack channel.

The default filter just checks for P85 with Autopilot -- modifying the filter is trivial:

```python
def filter_p85_autopilot(df):
    return df[df['isAutopilot'] & df['Badge'].isin(['P85', 'P85+'])]
```

## Usage
```bash
$ python crawler.py \
    --slack-token='TOKEN' \
    --slack-username 'tesla-crawler'\
    --slack-channel='teslas'
```
