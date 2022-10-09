"""Retrieve and parse a release from GitHub."""

from __future__ import annotations

import urllib.request as urq
import logging
import io
from zipfile import ZipFile

from ziprepo import ZipRepo


def get_data(config):
    """Get the configured release from GitHub; return a ZipRepo for it."""

    # Construct url and optional authorization header
    gh = config['GitHub']
    url = f"https://github.com/{gh.user}/{gh.repo}/archive/{gh.tag}.zip" 
    headers = { 'Authorization': f'token { gh.token}' } if  gh.token else {}
    
    # Retrieve data and create ZipFile object
    logging.info('Retrieving %s\n', url)
    rq = urq.Request(url, headers=headers)
    with urq.urlopen(rq) as rsp:
        data = io.BytesIO(rsp.read())
    zf = ZipFile(data)

    # Create ZipRepo object, and parse the data
    repo = ZipRepo(config, zf)
    repo.get_names()
    
    return repo


