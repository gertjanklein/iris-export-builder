"""Retrieve and parse a release from Bitbucket."""

from __future__ import annotations

import logging
import io
from zipfile import ZipFile

import requests

from ziprepo import ZipRepo


def get_data(config):
    """Get the configured release from Bitbucket; return a ZipRepo for it."""

    # Construct url and optional authorization header
    bb = config['Bitbucket']
    url = f"https://bitbucket.org/{bb.owner}/{bb.repo}/get/{bb.tag}.zip"
    auth = (bb.user, bb.token) if (bb.user + bb.token != '') else None
    
    # Retrieve data and create ZipFile object
    logging.info('Retrieving %s\n', url)
    with requests.get(url, auth=auth, timeout=60) as rsp:
        data = io.BytesIO(rsp.content)
    zf = ZipFile(data)

    # Create ZipRepo object, and parse the data
    repo = ZipRepo(config, zf)
    repo.get_names()
    
    return repo
