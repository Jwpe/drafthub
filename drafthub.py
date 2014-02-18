import requests
import os
import re
import base64
import json

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

def sync():

    docs_uri = DRAFT_URI + 'documents.json'

    draft_resp = requests.get(docs_uri, auth=(DRAFT_USERNAME, DRAFT_PASSWORD))

    draft_resp.raise_for_status()

    documents = draft_resp.json()

    repo_uri = "/".join([GITHUB_URI, 'repos', 'Jwpe', 'draft-posts'])

    contents_uri = "/".join([repo_uri, 'contents'])

    github_resp = requests.get(contents_uri, auth=(GITHUB_USERNAME, GITHUB_PASSWORD))

    github_resp.raise_for_status()

    repo_contents = github_resp.json()
    slug_names = [item.get('name') for item in repo_contents]
    sha_map = {item['name']:item['sha'] for item in repo_contents}

    for document in documents:
        doc_name = document.get('name')
        doc_timestamp = document.get('updated_at')

        if doc_name:
            slug_name = slugify(doc_name) + '.md'

            # Bloody unicode
            try:
                encoded_data = base64.b64encode(document.get('content'))
            except UnicodeEncodeError:
                continue

            data = {
                'content': encoded_data,
            }

            if slug_name in slug_names:
                # If the file already exists we need to provide the SHA
                message_verb = "Updated"
                data['sha'] = sha_map.get(slug_name)
            else:
                message_verb = "Created"

            data['message'] = "{} {} at {}".format(message_verb, doc_name,
                doc_timestamp)

            github_doc_uri = "/".join([contents_uri, slug_name])

            # Put request to github
            response = requests.put(github_doc_uri, json.dumps(data), auth=(GITHUB_USERNAME, GITHUB_PASSWORD))

            response.raise_for_status()

            print data['message']

if __name__ == '__main__':
    sync()

