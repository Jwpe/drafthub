import requests
import sys
import os
import re
import base64
import json
import time

DRAFT_USERNAME = os.environ.get('DRAFT_USERNAME')
DRAFT_PASSWORD = os.environ.get('DRAFT_PASSWORD')

DRAFT_URI = 'https://draftin.com/api/v1/'

GITHUB_USERNAME = os.environ.get('GITHUB_USERNAME')
GITHUB_PASSWORD = os.environ.get('GITHUB_PASSWORD')

GITHUB_URI = 'https://api.github.com'


def slugify(doc_name):
    """Slugify function adapted from Django's."""
    doc_name = re.sub('[^\w\s-]', '', doc_name).strip().lower()
    return re.sub('[-\s]+', '_', doc_name)

def get_docs():

    docs_uri = DRAFT_URI + 'documents.json'

    draft_resp = requests.get(docs_uri, auth=(DRAFT_USERNAME, DRAFT_PASSWORD))
    draft_resp.raise_for_status()

    return draft_resp.json()

def get_contents_uri(repository):

    repo_uri = "/".join([GITHUB_URI, 'repos', GITHUB_USERNAME, repository])
    return "/".join([repo_uri, 'contents'])

def get_dir(repository, directory=''):

    uri = get_contents_uri(repository)
    if directory:
        uri = "/".join([uri, directory])
    response = requests.get(uri, auth=(GITHUB_USERNAME, GITHUB_PASSWORD))

    # If the directory does not exist, treat it as empty
    if response.status_code == 404:
        return []

    response.raise_for_status()
    return response.json()

def update_file(data, repo_name, file_name, ext, path=''):

    if path:
        file_path = '/'.join([get_contents_uri(repo_name), path])
    else:
        file_path = get_contents_uri(repo_name)

    uri = '/'.join([file_path, file_name + ext])

    response = requests.put(
        uri, json.dumps(data), auth=(GITHUB_USERNAME, GITHUB_PASSWORD))
    response.raise_for_status()

    # Avoid race conditions with github's contents API
    time.sleep(1)

    return response

def get_filename(file_path):
    return os.path.splitext(file_path)[0]

def sha_map(dir_contents):
    return {get_filename(item['name']):item['sha'] for item in dir_contents}

def sync():

    try:
        repo_name = sys.argv[1]
    except IndexError:
        print "Error: Please enter a repository name, e.g. python drafthub.py <repo_name>."
        return

    documents = get_docs()
    source_contents = get_dir(repo_name, 'source')
    html_contents = get_dir(repo_name, 'html')

    source_sha_map = sha_map(source_contents)
    html_sha_map = sha_map(html_contents)

    slug_names = [get_filename(item.get('name')) for item in source_contents]

    for document in documents:
        doc_name = document.get('name')
        doc_timestamp = document.get('updated_at')

        if doc_name:
            slug_name = slugify(doc_name)
            source = document.get('content').encode('utf-8')
            html = document.get('content_html').encode('utf-8')

            source_data = {'content': base64.b64encode(source)}
            html_data = {'content': base64.b64encode(html)}

            if slug_name in slug_names:
                # If the file already exists we need to provide the SHA
                message_verb = 'Updated'
                source_data['sha'] = source_sha_map.get(slug_name)
                html_data['sha'] = html_sha_map.get(slug_name)
            else:
                message_verb = 'Created'

            message = '{verb} {name} at {timestamp}'.format(verb=message_verb,
                name=doc_name, timestamp=doc_timestamp)

            source_data['message'] = message + ' (MD)'
            html_data['message'] = message + ' (HTML)'

            update_file(source_data, repo_name, slug_name, '.md', 'source')
            update_file(html_data, repo_name, slug_name, '.html', 'html')

            print source_data['message']
            print html_data['message']

if __name__ == '__main__':
    sync()

