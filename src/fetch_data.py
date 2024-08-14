import praw

# Reddit API credentials
reddit = praw.Reddit(
    client_id="E_D2zCfnX2FMMQoB9wlDPw",
    client_secret="Dwz72QR2tmyL0NgOmArU7vXEYyK_-w",
    user_agent="linux:com.example.greentext:v1 (by /u/NigwardTesticles)",
)


def getSubmissionTitle(url):
    submission_id = reddit.submission(url=url).id
    title = reddit.submission(submission_id).title
    return title

def getSubmissionBody(url):
    submission_id = reddit.submission(url=url).id
    body = reddit.submission(submission_id).selftext
    return body

