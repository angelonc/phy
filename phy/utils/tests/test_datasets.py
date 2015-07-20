# -*- coding: utf-8 -*-

"""Tests of dataset utility functions."""

#------------------------------------------------------------------------------
# Imports
#------------------------------------------------------------------------------

import os.path as op
from itertools import product

import numpy as np
from numpy.testing import assert_array_equal as ae
import responses
from pytest import raises, yield_fixture

from ..datasets import (_download,
                        download_file,
                        download_test_data,
                        download_sample_data,
                        _check_md5_of_url,
                        _BASE_URL,
                        )


#------------------------------------------------------------------------------
# Fixtures
#------------------------------------------------------------------------------

# Test URL and data
_URL = 'http://test/data'
_DATA = np.linspace(0., 1., 100000).astype(np.float32)
_CHECKSUM = '7d257d0ae7e3af8ca3574ccc3a4bf072'


def _add_mock_response(url, body, file_type='binary'):
    content_type = ('application/octet-stream'
                    if file_type == 'binary' else 'text/plain')
    responses.add(responses.GET, url,
                  body=body,
                  status=200,
                  content_type=content_type,
                  )


@yield_fixture
def mock_url():
    data = _DATA.tostring()
    checksum = _CHECKSUM
    url_data = _URL
    url_checksum = _URL + '.md5'

    _add_mock_response(url_data, data)
    _add_mock_response(url_checksum, checksum)

    yield

    responses.reset()


@yield_fixture(params=product((True, False), repeat=4))
def mock_urls(request):
    data = _DATA.tostring()
    checksum = _CHECKSUM
    url_data = _URL
    url_checksum = _URL + '.md5'

    if not request.param[0]:
        # Data URL is corrupted.
        url_data = url_data[:-1]
    if not request.param[1]:
        # Data is corrupted.
        data = data[:-1]
    if not request.param[2]:
        # Checksum URL is corrupted.
        url_checksum = url_checksum[:-1]
    if not request.param[3]:
        # Checksum is corrupted.
        checksum = checksum[:-1]

    _add_mock_response(url_data, data)
    _add_mock_response(url_checksum, checksum)

    yield request.param, url_data, url_checksum

    responses.reset()


#------------------------------------------------------------------------------
# Test utility functions
#------------------------------------------------------------------------------

@responses.activate
def test_check_md5_of_url(tempdir, mock_url):
    output_path = op.join(tempdir, 'data')
    download_file(_URL, output_path)
    _check_md5_of_url(output_path, _URL)


#------------------------------------------------------------------------------
# Test download functions
#------------------------------------------------------------------------------

@responses.activate
def test_download_not_found(tempdir):
    path = op.join(tempdir, 'test')
    with raises(Exception):
        download_file(_URL + '_notfound', path)


@responses.activate
def test_download_checksum():
    assert _download(_URL + '.md5') == _CHECKSUM


@responses.activate
def test_download_file(tempdir, mock_urls):
    path = op.join(tempdir, 'test.kwik')
    param, url_data, url_checksum = mock_urls
    data_here, data_valid, checksum_here, checksum_valid = param

    def _dl():
        download_file(url_data, path, checksum=_CHECKSUM)
        with open(path, 'rb') as f:
            data = f.read()
        return data

    def _check(data):
        ae(np.fromstring(data, np.float32), _DATA)

    assert_succeeds = (data_here and data_valid and
                       ((checksum_here == checksum_valid) or
                        (not(checksum_here) and checksum_valid)))

    download_succeeds = (assert_succeeds or (data_here and
                         (not(data_valid) and not(checksum_here))))

    if download_succeeds:
        data = _dl()
    else:
        with raises(Exception):
            data = _dl()

    if assert_succeeds:
        _check(data)


@responses.activate
def test_download_sample_data(tempdir):
    name = 'sample'
    url = _BASE_URL['cortexlab'] + name
    for ext in ('.kwik', '.kwx', '.raw.kwd'):
        _add_mock_response(url + ext, _DATA.tostring())
        _add_mock_response(url + ext + '.md5', _CHECKSUM)

    output_dir = op.join(tempdir, name)
    download_sample_data(name, output_dir)
    for ext in ('.kwik', '.kwx', '.raw.kwd'):
        with open(op.join(output_dir, name + ext), 'rb') as f:
            data = f.read()
        ae(np.fromstring(data, np.float32), _DATA)


@responses.activate
def test_dat_file(tempdir):
    data = np.random.randint(size=(20000, 4),
                             low=-100, high=100).astype(np.int16)
    fn = 'test-4ch-1s.dat'
    _add_mock_response(_BASE_URL['github'] + 'test/' + fn,
                       data.tostring())

    path = _download_test_data(fn, tempdir)
    with open(path, 'rb') as f:
        arr = np.fromfile(f, dtype=np.int16).reshape((-1, 4))
    assert arr.shape == (20000, 4)
