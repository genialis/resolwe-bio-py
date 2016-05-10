"""Resolwe"""
from __future__ import absolute_import, division, print_function

import json
import os
import re
import sys
import uuid
import ntpath

import requests
import slumber

from six.moves.urllib.parse import urljoin  # pylint: disable=import-error

from requests.exceptions import ConnectionError  # pylint: disable=ungrouped-imports, redefined-builtin

from .resources import Data, Collection, Sample
from .resources.utils import iterate_schema


CHUNK_SIZE = 90000000
DEFAULT_EMAIL = 'anonymous@genialis.com'
DEFAULT_PASSWD = 'anonymous'
DEFAULT_URL = 'https://dictyexpress.research.bcm.edu'


class Resolwe(object):
    """Python API for Resolwe Bioinformatics."""

    def __init__(self, email=DEFAULT_EMAIL, password=DEFAULT_PASSWD, url=DEFAULT_URL):
        """
        Connect to Resolwe on desired url and provide credentials.
        """
        self.url = url
        self.auth = ResAuth(email, password, url)
        self.api = slumber.API(urljoin(url, '/api/'), self.auth, append_slash=False)

        self.data = ResolweQuerry(self, Data)
        self.collection = ResolweQuerry(self, Collection)
        self.sample = ResolweQuerry(self, Sample)

        # data = dict of (data_id - Data object) pairs
        # collections = dict of (collection_id - Collection object) pairs
        # collections_data - dict of (collection_id - Data objects list) pairs,
        self.cache = {'data': {}, 'collections': None, 'collections_data': {}}
        # TODO: what if there are updates on server? How to know when to update cache?

    def processes(self, process_name=None):
        """Return a list of Processor objects.

        :param process_name: Name of the process
        :type process_name: string
        :rtype: list of Process objects

        """
        # TODO: Make a better representation? If this is run from command line
        # it outputs thousands of lines... Not really helpful.
        if process_name:
            return [p for p in self.api.process.get() if process_name in p['name']]
        else:
            return self.api.process.get()

    def print_upload_processes(self):
        """Print all upload process names."""
        for process in self.processes():
            if 'upload' in process['category']:
                sys.stdout.write(process['name'] + '\n')

    def print_process_inputs(self, process_name):
        """Print process input fields and types.

        :param process_name: Process object name
        :type process_name: string

        """
        process = self.processes(process_name=process_name)

        if len(process) == 1:
            process = process[0]
        elif len(process) > 1:
            # Multiple processors with same slug, but different versions:
            versions = ([int(x['version']) for x in process])
            # Get index of the latest processor version:
            top_index = sorted(enumerate(versions), key=lambda x: x[1])[-1][0]
            process = process[top_index]
        else:
            raise ValueError('Invalid process name: {}.'.format(process_name))

        for field_schema, _, _ in iterate_schema({}, process['input_schema'], 'input'):
            name = field_schema['name']
            typ = field_schema['type']
            sys.stdout.write("{} -> {}\n".format(name, typ))

    def create(self, data, resource='data'):
        """Create an object of resource:

        * data
        * collection
        * process
        * trigger
        * template

        :param data: Object values
        :type data: dict
        :param resource: Resource name
        :type resource: string

        """
        if isinstance(data, dict):
            data = json.dumps(data)

        if not isinstance(data, str):
            raise ValueError('Data must be dict, str or unicode.')

        resource = resource.lower()
        if resource not in ('data', 'collection', 'process', 'trigger', 'template'):
            raise ValueError('Resource must be data, collection, process, trigger or template.')

        url = urljoin(self.url, '/api/{}'.format(resource))
        return requests.post(url,
                             data=data,
                             auth=self.auth,
                             headers={
                                 'cache-control': 'no-cache',
                                 'content-type': 'application/json',
                                 'accept': 'application/json, text/plain, */*',
                                 'referer': self.url,
                             })

    def upload(self, process_name, name='', descriptor=None, descriptor_schema=None,
               collections=[], **fields):

        """Upload files and data objects.

        :param collections: Integer id of Resolwe collection
        :type collections: List of int
        :param process_name: Processor object name
        :type process_name: string
        :param fields: Processor field-value pairs
        :type fields: args
        :rtype: HTTP Response object

        """
        # This is temporary solution: map process name to it's ID:
        proc_name_to_slug = dict([(x['name'], x['slug']) for x in self.processes()])

        process = self.processes(process_name=process_name)

        if len(process) == 1:
            process = process[0]
        elif len(process) > 1:
            # Multiple processors with same slug, but different versions:
            versions = ([int(x['version']) for x in process])
            # Get index of the latest processor version:
            top_index = sorted(enumerate(versions), key=lambda x: x[1])[-1][0]
            process = process[top_index]
        else:
            raise ValueError('Invalid process name: {}.'.format(process_name))

        inputs = {}

        for field_name, field_val in fields.items():
            input_fields = dict([(e['name'], e['type']) for e in process['input_schema']])
            if field_name not in input_fields.keys():
                raise ValueError(
                    "Field {} not in process {} inputs.".format(field_name, process['name']))

            if input_fields[field_name].startswith('basic:file:'):
                if not os.path.isfile(field_val):
                    raise ValueError("File {} not found.".format(field_val))

                file_temp = self._upload_file(field_val)

                if not file_temp:
                    raise Exception("Upload failed for {}.".format(field_val))

                file_name = ntpath.basename(field_val)
                inputs[field_name] = {
                    'file': file_name,
                    'file_temp': file_temp
                }
            else:
                inputs[field_name] = field_val

        data = {
            'status': 'uploading',
            'process': proc_name_to_slug[process_name],
            'input': inputs,
            'slug': str(uuid.uuid4()),
            'name': name,
        }

        if descriptor:
            data['descriptor'] = descriptor

        if descriptor_schema:
            data['descriptor_schema'] = descriptor_schema

        if len(collections) > 0:
            data['collections'] = collections

        return self.create(data)

    def _upload_file(self, fn):
        """Upload a single file on the platform.

        File is uploaded in chunks of 1,024 bytes.

        :param fn: File path
        :type fn: string

        """
        response = None
        chunk_number = 0
        session_id = str(uuid.uuid4())
        file_size = os.path.getsize(fn)
        base_name = os.path.basename(fn)

        with open(fn, 'rb') as file_:
            while True:
                chunk = file_.read(CHUNK_SIZE)
                if not chunk:
                    break

                for i in range(5):
                    if i > 0 and response is not None:
                        sys.stdout.write("Chunk upload failed (error {}): repeating for chunk \
                                         number {}".format(response.status_code, chunk_number))

                    response = requests.post(urljoin(self.url, 'upload/'),
                                             auth=self.auth,

                                             # request are smart and make
                                             # 'CONTENT_TYPE': 'multipart/form-data;''
                                             files={'file': (base_name, chunk)},

                                             # stuff in data will be in response.POST on server
                                             data={
                                                 '_chunkSize': CHUNK_SIZE,
                                                 '_totalSize': file_size,
                                                 '_chunkNumber': chunk_number,
                                                 '_currentChunkSize': len(chunk),
                                             },
                                             headers={
                                                 'Session-Id': session_id
                                             })
                    if response.status_code in [200, 201]:
                        break
                else:
                    # Upload of a chunk failed (5 retries)
                    return None

                progress = 100. * (chunk_number * CHUNK_SIZE + len(chunk)) / file_size
                sys.stdout.write("\n{:.0f} % Uploaded {}".format(progress, fn))
                sys.stdout.flush()
                chunk_number += 1

        sys.stdout.write("\n")
        return response.json()['files'][0]['temp']

    def download(self, data_objects, field):
        """Download files of data objects.

        :param data_objects: Data object ids
        :type data_objects: list of integers
        :param field: Download field name
        :type field: string
        :rtype: generator of requests.Response objects

        """
        if not field.startswith('output'):
            raise ValueError("Only process results (output.* fields) can be downloaded.")

        for obj in data_objects:
            if re.match(r'^\d+$', str(obj)) is None:
                raise ValueError("Invalid object id {}.".format(obj))

            if obj not in self.cache['data']:
                try:
                    self.cache['data'][obj] = Data(self.api.data(obj).get(), self)
                except slumber.exceptions.HttpNotFoundError:
                    raise ValueError("Data id {} does not exist.".format(obj))

            if field not in self.cache['data'][obj].annotation:
                raise ValueError("Field {} does not exist for data object {}.".format(field, obj))

            ann = self.cache['data'][obj].annotation[field]
            if ann['type'] != 'basic:file:':
                raise ValueError("Only basic:file: fields can be downloaded.")

        for obj in data_objects:
            ann = self.cache['data'][obj].annotation[field]
            url = urljoin(self.url, 'data/{}/{}'.format(obj, ann['value']['file']))
            response = requests.get(url, stream=True, auth=self.auth)
            if not response.ok:
                response.raise_for_status()
            else:
                return response


class ResAuth(requests.auth.AuthBase):

    """
    Attach HTTP Resolwe Authentication to Request object.
    """

    def __init__(self, email=DEFAULT_EMAIL, password=DEFAULT_PASSWD, url=DEFAULT_URL):
        payload = {'username': email, 'password': password}

        try:
            response = requests.post(urljoin(url, '/rest-auth/login/'), data=payload)
        except ConnectionError:
            raise ValueError('Server not accessible on {}. Wrong url?'.format(url))

        status_code = response.status_code
        if status_code in [400, 403]:
            raise ValueError('Response HTTP status code {}. Invalid credentials?'.format(status_code))

        if not ('sessionid' in response.cookies and 'csrftoken' in response.cookies):
            raise Exception('Missing sessionid or csrftoken. Invalid credentials?')

        self.sessionid = response.cookies['sessionid']
        self.csrftoken = response.cookies['csrftoken']
        # self.subscribe_id = str(uuid.uuid4())

    def __call__(self, request):
        # modify and return the request
        request.headers['Cookie'] = 'csrftoken={}; sessionid={}'.format(self.csrftoken,
                                                                        self.sessionid)
        request.headers['X-CSRFToken'] = self.csrftoken

        # Not needed until we support HTTP Push with the API
        # if r.path_url != '/upload/':
        #     r.headers['X-SubscribeID'] = self.subscribe_id
        return request


class ResolweQuerry(object):
    """
    Enable querries on data, collection and sample endpoints in Resolwe.

    Each Resolwe instance (for example "re") has threee "endpoints": re.data,
    re.collections and re.sample. Each such andpooint is an instance of
    ResolweQuerry class. ResolweQuerry enables querries on
    corresponding objects, for example:

    re.data.get(42) # return Data object with ID 42.
    re.sample.filter(contributor=1) # return all samples made by contributor 1

    Detailed description of methods can be found in method docstrings.
    """

    def __init__(self, resolwe, Resource):
        self.resolwe = resolwe
        self.resource = Resource
        self.endpoint = Resource.endpoint
        self.api = getattr(resolwe.api, Resource.endpoint)

    def get(self, uid):
        """
        Get object with provided ID or slug.

        :param uid: unique identifier - ID or slug
        :type uid: int(ID) or string(slug)

        :rtype: object of type self.resource
        """
        try:
            if re.match('^[0-9]+$', str(uid)):  # iud is ID number:
                return self.resource(self.api(str(uid)).get(), self.resolwe)
            else:  # uid is slug
                return self.resource(self.api.get(slug=uid)[0], self.resolwe)
        except slumber.exceptions.HttpNotFoundError:
            raise ValueError('Id: "{}" does not exist or you dont have access '
                             'permission.'.format(str(uid)))
        except IndexError:
            raise ValueError('Slug: "{}" does not exist or you dont have '
                             'access permission.'.format(uid))

    def filter(self, **kwargs):
        """
        Return a list of Data objects that match kwargs.

        Querries can be made with the following keywords (and operators)
            * Fields (and operators) for **data** endpoint:
                * slug (=)
                * contributor (=)
                * status (=)
                * name (=)
                * created (=)
                * modified (=)
                * input (=)
                * descriptor (=)
                * started (=)
                * finished (=)
                * output (=)
                * process (=)
                * type (=)
                * collection (=)
            * Fields (and operators) for **collecction** and **sample** endpoint:
                * contributor (=)
                * name (=)
                * description (=)
                * created (=)
                * modified (=)
                * slug (=)
                * descriptor (=)
                * data (=)
                * descriptor_schema (=)
                * id (=)

        Example usage:
        # Get a list of data objects with status set to OK.
        re.data.filter(status='OK')
        # Get a liust of sample objects that contain data object 42 and
        # were contributed by contibutor with ID 1
        re.collection.filter(data=42, contributor=1)

        Note: The filtering options might change (improve) with time.
        """
        return [self.resource(x, self.resolwe) for x in self.api.get(**kwargs)]

    def search(self):
        """
        Full text search.
        """
        raise NotImplementedError()
