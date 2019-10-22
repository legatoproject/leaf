"""
Leaf Package Manager

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
"""

import os
import shutil
import time
from pathlib import Path
from urllib.parse import urlparse, urlunparse
from urllib.request import urlopen

import requests

from leaf.core.constants import LeafSettings
from leaf.core.logger import TextLogger, print_trace
from leaf.core.utils import hash_check

PRIORITIES_RANGE = range(1, 1000)
PROTOCOLS_PRIORITIES = {"https": 200, "http": 201, "file": 100, "": 100}


def get_url_priority(url: str):
    return PROTOCOLS_PRIORITIES.get(urlparse(url).scheme, 500)


def url_resolve(url: str, subpath: str):
    """
    Resolves a relative URL
    """
    url = urlparse(url)
    newpath = Path(url.path).parent / subpath
    url = url._replace(path=str(newpath))
    return urlunparse(url)


def _download_file_generic(url: str, output: Path, logger: TextLogger):
    _display_progress(logger, "Getting {0.name}".format(output))
    with urlopen(url, timeout=LeafSettings.DOWNLOAD_TIMEOUT.as_int()) as stream:
        with output.open("wb") as fp:
            fp.write(stream.read())
    # End the progress display
    _display_progress(logger, "Getting {0.name}".format(output), 1, 1, end="\n")


def _download_file_local(url: str, output: Path, logger: TextLogger):
    _display_progress(logger, "Copying {0.name}".format(output))
    shutil.copy(str(url), str(output))
    # End the progress display
    _display_progress(logger, "Copying {0.name}".format(output), 1, 1, end="\n")


def _download_file_http(url: str, output: Path, logger: TextLogger, resume: bool = None, retry: int = None, buffer_size: int = 262144):
    # Handle default values
    if retry is None:
        retry = LeafSettings.DOWNLOAD_RETRY.as_int()
    if resume is None:
        resume = not LeafSettings.DOWNLOAD_NORESUME.as_boolean()

    _display_progress(logger, "Downloading {0.name}".format(output))

    iteration = 0
    while True:
        try:
            headers = {}
            size_current = 0
            if output.exists():
                if resume:
                    size_current = output.stat().st_size
                    headers = {"Range": "bytes={0}-".format(size_current)}
                else:
                    output.unlink()

            with output.open("ab" if resume else "wb") as fp:
                req = requests.get(url, stream=True, headers=headers, timeout=LeafSettings.DOWNLOAD_TIMEOUT.as_int())
                # Get total size on first request
                size_total = int(req.headers.get("content-length", -1)) + size_current

                # Read remote data and write to output file
                for data in req.iter_content(buffer_size):
                    size_current += fp.write(data)
                    _display_progress(logger, "Downloading {0.name}".format(output), size_current, size_total)

                # Rare case when no exception raised and download is not finished
                if 0 < size_current < size_total:
                    raise ValueError("Incomplete download")

                # End the progress display
                _display_progress(logger, "Downloading {0.name}".format(output), 1, 1, end="\n")
                return size_current
        except (ValueError, requests.RequestException, requests.ConnectionError, requests.HTTPError, requests.Timeout) as e:
            iteration += 1
            # Check retry
            if iteration > retry:
                raise e
            # Log the retry attempt
            if logger:
                logger.print_default("\nError while downloading, retry {0}/{1}".format(iteration, retry))
            print_trace()
            # Prevent imediate retry
            time.sleep(1)


def download_file(url: str, output: Path, logger: TextLogger = None):
    # Create parent folder if needed
    if not output.parent.exists():
        output.parent.mkdir(parents=True)
    # Parse url to get the protocole
    parsedurl = urlparse(url)
    if parsedurl.scheme == "":
        # file mode, simple file copy
        _download_file_local(parsedurl.path, output, logger=logger)
    elif parsedurl.scheme.startswith("http"):
        # http/https mode, get file length before
        _download_file_http(url, output, logger=logger)
    else:
        # other scheme, use urllib
        _download_file_generic(url, output, logger=logger)


def download_and_verify_file(url: str, output: Path, logger: TextLogger = None, hashstr: str = None):
    """
    Download an artifact and check its hash if given
    """
    if output.exists():
        if hashstr is None:
            logger.print_verbose("File exists but cannot be verified, {file.name} will be re-downloaded".format(file=output))
            os.remove(str(output))
        elif not hash_check(output, hashstr, raise_exception=False):
            logger.print_verbose("File exists but hash differs, {file.name} will be re-downloaded".format(file=output))
            os.remove(str(output))
        else:
            logger.print_verbose("File {file.name} is already downloaded".format(file=output))

    if not output.exists():
        download_file(url, output, logger=logger)
        if hashstr:
            hash_check(output, hashstr, raise_exception=True)
    return output


def _display_progress(logger: TextLogger, message: str, worked: int = None, total: int = None, end: str = "", try_percent=True):
    if logger:
        if worked is None or total is None:
            logger.print_default(message, end=end, flush=True)
        else:
            kwargs = {"message": message, "worked": worked, "total": total, "progress": "??"}
            if try_percent and 0 <= worked <= total and total > 0:
                kwargs["progress"] = "{0:.0%}".format(worked / total)
            else:
                kwargs["progress"] = "{0}/{1}".format(worked, total)
            logger.print_default("\r[{progress}] {message} ".format(**kwargs), end=end, flush=True)
