# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# Copyright The Cloud Custodian Authors.
# SPDX-License-Identifier: Apache-2.0
import pygit2
import click
import docker
import json

from datetime import datetime, timedelta
from dateutil.tz import tzoffset, tzutc
from dateutil.parser import parse as parse_date

from c7n.resources import load_available
from c7n.schema import resource_outline


def commit_date(commit):
    tzinfo = tzoffset(None, timedelta(minutes=commit.author.offset))
    return datetime.fromtimestamp(float(commit.author.time), tzinfo)


aliases = {
    'c7n': 'core',
    'cli': 'core',
    'c7n_mailer': 'tools',
    'mailer': 'tools',
    'utils': 'core',
    'cask': 'tools',
    'test': 'tests',
    'docker': 'core',
    'dockerfile': 'tools',
    'asg': 'aws',
    'build': 'tests',
    'aws lambda policy': 'aws',
    'tags': 'aws',
    'notify': 'core',
    'sechub': 'aws',
    'sns': 'aws',
    'actions': 'aws',
    'serverless': 'core',
    'packaging': 'tests',
    '0': 'release',
    'dep': 'core',
    'ci': 'tests'}

skip = set(('release', 'merge'))


def resolve_dateref(since, repo):
    try:
        since = repo.lookup_reference('refs/tags/%s' % since)
    except KeyError:
        since = parse_date(since).astimezone(tzutc())
    else:
        since = commit_date(since.peel())
    return since


def schema_outline_from_docker(tag):
    client = docker.from_env()
    result = client.containers.run(
        f"cloudcustodian/c7n:{tag}",
        "schema --outline --json"
    )
    return json.loads(result)


def schema_diff(schema_old, schema_new):
    out = []
    for provider in schema_new:
        resources_old = schema_old.get(provider, [])
        resources_new = schema_new[provider]
        for resource in sorted(set(list(resources_old) + list(resources_new))):
            if resource not in resources_old:
                out.append(f"- `{resource}` added")
            elif resource not in resources_new:
                out.append(f"- `{resource}` removed")
            else:
                actions_added = [
                    action for action in resources_new[resource]['actions']
                    if action not in resources_old[resource]['actions']
                ]
                actions_removed = [
                    action for action in resources_old[resource]['actions']
                    if action not in resources_new[resource]['actions']
                ]
                filters_added = [
                    action for action in resources_new[resource]['filters']
                    if action not in resources_old[resource]['filters']
                ]
                filters_removed = [
                    action for action in resources_old[resource]['filters']
                    if action not in resources_new[resource]['filters']
                ]

                if any([
                    actions_added, actions_removed,
                    filters_added, filters_removed,
                ]):
                    out.append(f"- `{resource}`")
                if actions_added:
                    li = ", ".join([f"`{a}`" for a in actions_added])
                    out.append(f"  - actions added: {li}")
                if actions_removed:
                    li = ", ".join([f"`{a}`" for a in actions_removed])
                    out.append(f"  - actions removed: {li}")
                if filters_added:
                    li = ", ".join([f"`{a}`" for a in filters_added])
                    out.append(f"  - filters added: {li}")
                if filters_removed:
                    li = ", ".join([f"`{a}`" for a in filters_removed])
                    out.append(f"  - filters removed: {li}")

    return "\n".join(out) + "\n"


@click.command()
@click.option('--path', required=True)
@click.option('--output', required=True)
@click.option('--since')
@click.option('--end')
@click.option('--user', multiple=True)
def main(path, output, since, end, user):
    repo = pygit2.Repository(path)
    if since:
        since_dateref = resolve_dateref(since, repo)
    if end:
        end_dateref = resolve_dateref(end, repo)

    groups = {}
    count = 0
    for commit in repo.walk(
            repo.head.target):
        cdate = commit_date(commit)
        if since and cdate <= since_dateref:
            break
        if end and cdate >= end_dateref:
            continue
        if user and commit.author.name not in user:
            continue

        parts = commit.message.strip().split('-', 1)
        if not len(parts) > 1:
            print("bad commit %s %s" % (cdate, commit.message))
            category = 'other'
        else:
            category = parts[0]
        category = category.strip().lower()
        if '.' in category:
            category = category.split('.', 1)[0]
        if '/' in category:
            category = category.split('/', 1)[0]
        if category in aliases:
            category = aliases[category]

        message = commit.message.strip()
        if '\n' in message:
            message = message.split('\n')[0]

        found = False
        for s in skip:
            if category.startswith(s):
                found = True
                continue
        if found:
            continue
        if user:
            message = "%s - %s - %s" % (cdate.strftime("%Y/%m/%d"), commit.author.name, message)
        groups.setdefault(category, []).append(message)
        count += 1

    import pprint
    print('total commits %d' % count)
    pprint.pprint(dict([(k, len(groups[k])) for k in groups]))

    diff_md = ""
    if since and not end:
        schema_old = schema_outline_from_docker(since)
        load_available()
        schema_new = resource_outline()
        diff_md = schema_diff(schema_old, schema_new)

    with open(output, 'w') as fh:
        for k in sorted(groups):
            if k in skip:
                continue
            print("# %s" % k, file=fh)
            for c in sorted(groups[k]):
                print(" - %s" % c.strip(), file=fh)
            print("\n", file=fh)
        if diff_md.strip():
            print("# schema diff", file=fh)
            print(diff_md, file=fh)


if __name__ == '__main__':
    main()
