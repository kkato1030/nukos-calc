import json
import yaml

from github import Github
from urllib import request


with open('./config.yml') as f:
    config = yaml.safe_load(f)

GITHUB_TOKEN = config['GITHUB_TOKEN']
SLACK_WEBHOOK_URL = config['SLACK_WEBHOOK_URL']
SLACK_TEAM_ID = config['SLACK_TEAM_ID']
TARGET_REPOSITORY = config['TARGET_REPOSITORY']

g = Github(GITHUB_TOKEN)
org = g.get_organization("PyGithub")

point_list = [1, 3, 5]
state_list = ['open', 'closed']


def main(event=None, context=None):
    main_velocity = None
    for repo_name in TARGET_REPOSITORY:
        repo = g.get_repo(repo_name)
        velocity = get_velocity(repo)
        if main_velocity is None:
            main_velocity = velocity
            continue

        merge_velocity(main_velocity, velocity)

    sorted_velocity = get_sorted_velocity(main_velocity)
    print(sorted_velocity)

    message = get_message(sorted_velocity)
    print(message)
    send_slack(message)


def get_milestone_number(repo, milestone_title):
    milestones = repo.get_milestones(state='all')
    for milestone in milestones:
        if milestone.title == milestone_title:
            return milestone.number

    raise 'Not Found'


def get_sorted_velocity(velocity):
    return sorted(velocity.items())


def get_velocity(repo, milestone='all'):
    if milestone == 'all':
        milestones = repo.get_milestones(state='open')
    else:
        number = get_milestone_number(repo, milestone)
        milestones = [repo.get_milestone(number=number)]

    velocity = {
        milestone.title: {
            'open': 0,
            'closed': 0,
            'sum': 0,
        }
        for milestone in milestones
    }
    for state in state_list:
        for point in point_list:
            open_issues = repo.get_issues(
                state=state,
                labels=[repo.get_label(f'Point-{point}')],
            )
            for issue in open_issues:
                if issue.milestone is None:
                    continue

                milestone = issue.milestone.title
                if velocity.get(milestone):
                    velocity[milestone][state] += point
                    velocity[milestone]['sum'] += point

    return velocity


def merge_velocity(vel1, vel2):
    for key in vel2:
        if key in vel1:
            vel1[key]['open'] += vel2[key]['open']
            vel1[key]['closed'] += vel2[key]['closed']
            vel1[key]['sum'] += vel2[key]['sum']
        else:
            vel1[key] = vel2[key]


def get_message(velocity):
    message = f'<!subteam^{SLACK_TEAM_ID}> 現在のポイントを発表します!\n'
    for itr in velocity:
        closed = itr[1]['closed']
        summary = itr[1]['sum']
        if summary == 0:
            ratio = 0
        else:
            ratio = closed / summary
        percent = '{:.0%}'.format(ratio)
        # progress bar
        prog_max = 20
        prog_closed = round(prog_max * ratio)
        prog_open = prog_max - prog_closed

        message += f"""
*{itr[0]}*
{percent} [{'#' * prog_closed}{'−' * prog_open}] {closed}/{summary}
"""

    return message


def send_slack(message):
    url = SLACK_WEBHOOK_URL
    headers = {
        'Content-Type': 'application/json; charset=utf-8'
    }
    method = 'POST'
    data = {
        'username': 'nuko',
        'text': message,
    }
    json_data = json.dumps(data).encode('utf-8')
    req = request.Request(
        url=url,
        data=json_data,
        headers=headers,
        method=method
    )
    request.urlopen(req, timeout=5)


if __name__ == '__main__':
    main()

