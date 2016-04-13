"""Resolwe"""
from __future__ import absolute_import, division, print_function, unicode_literals

import json
import os
import re
import sys
import uuid
import ntpath

if sys.version_info < (3, ):
    import urlparse
else:
    from urllib import parse as urlparse

import requests
import slumber

from .data import Data
from .collection import Collection
from .utils import find_field, iterate_schema


CHUNK_SIZE = 10000
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
        self.api = slumber.API(urlparse.urljoin(url, '/api/'), self.auth, append_slash=False)


        # Defines cache to reuse the data already downloaded.
        #
        # data = dict of (data_id - Data) pairs
        # collections = dict of (collection_id - collection) pairs
        # collections_data - dict of (collection_id - data_list) pairs,
        #   where data_list is list of all data objects for given collection_id
        self.cache = {'data': {}, 'collections': None, 'collections_data': {}}
        # How about when the sever is changed - how can we get the changes? For example someone adds a collection or some data. Cache does not know this and cannot update?
        # this cache thing is just partially implemented now...

    def collections(self):
        """Return a list :obj:`Collection` collections.

        :rtype: list of :obj:`Collection` collections

        """
        if not ('collections' in self.cache and self.cache['collections']):
            self.cache['collections'] = {c['id']: Collection(c, self) for c in self.api.collection.get()}
        return self.cache['collections']

    def collection_data(self, collection):
        """Return a list of Data objects for a given collection.

        :param collection: ObjectId or slug of a collection
        :type collection: string
        :rtype: list of Data objects

        """
        #
        cache_collections_data = self.cache['collections_data']
        cache_data = self.cache['objects']
        collection_id = str(collection)

        if not re.match('^[0-9]+$', collection_id):
            # collection_id is a slug - transform it to collection_id number
            collections = [c for c in self.api.collection.get() if c['slug'] == collection_id]
            if len(collections) != 1:
                raise ValueError(msg='Attribute collection not a slug or ObjectId: {}'.format(collection_id))

            collection_id = str(collections[0]['id'])

        if collection_id not in cache_collections_data:
            cache_collections_data[collection_id] = []
            # data = [d for d in self.api.data.get() if d['slug'] == "slug1"]
            data = [d for d in self.api.data.get()]
            # Here you can make a smart querry.. ask Domen!
            # print(data)
            # data = all data for given collection
            self.api.data.get(case_ids__contains=collection_id)
            for d in data:
                _id = d['id']
                if _id in objects:
                    # Update existing object
                    objects[_id].update(d)
                else:
                    # Insert new object
                    objects[_id] = Data(d, self)

                cache_collections_data[collection_id].append(objects[_id])

            # Hydrate reference fields
            # = what does this mean?
            for d in cache_collections_data[collection_id]:
                while True:
                    ref_annotation = {}
                    remove_annotation = []
                    for path, ann in d.annotation.items():
                        if ann['type'].startswith('data:'):
                            # Referenced data object found
                            # Copy annotation
                            if ann['value'] in self.cache['objects']:
                                annotation = self.cache['objects'][ann['value']].annotation
                                ref_annotation.update({path + '.' + k: v for k, v in annotation.items()})

                            remove_annotation.append(path)
                    if ref_annotation:
                        d.annotation.update(ref_annotation)
                        for path in remove_annotation:
                            del d.annotation[path]
                    else:
                        break

        # what is there were changes on the server and there are new data?
        # update cache?
        return cache_collections_data[collection_id]

    def data(self, **query):
        """Query for Data object annotation.

        What does this mean? What kind of querry can this be?
        """
        objects = self.cache['objects']
        data = self.api.data.get(**query)['objects']
        data_objects = []

        for d in data:
            _id = d['id']
            if _id in objects:
                # Update existing object
                objects[_id].update(d)
            else:
                # Insert new object
                objects[_id] = Data(d, self)

            data_objects.append(objects[_id])

        # Hydrate reference fields
        for d in data_objects:
            count += 1
            while True:
                ref_annotation = {}
                remove_annotation = []
                for path, ann in d.annotation.items():
                    if ann['type'].startswith('data:'):
                        # Referenced data object found
                        # Copy annotation
                        _id = ann['value']
                        if _id not in objects:
                            try:
                                d_tmp = self.api.data(_id).get()
                            except slumber.exceptions.HttpClientError as ex:
                                if ex.response.status_code == 404:
                                    continue
                                else:
                                    raise ex

                            objects[_id] = Data(d_tmp, self)

                        annotation = objects[_id].annotation
                        ref_annotation.update({path + '.' + k: v for k, v in annotation.items()})
                        remove_annotation.append(path)
                if ref_annotation:
                    d.annotation.update(ref_annotation)
                    for path in remove_annotation:
                        del d.annotation[path]
                else:
                    break

        return data_objects

    def processes(self, process_name=None):
        """Return a list of Processor objects.

        :param process_name: Name of the process
        :type process_name: string
        :rtype: list of Process objects

        """
        if process_name:
            return [p for p in self.api.process.get() if process_name in p['name']]
        else:
            return self.api.process.get()

    def printad_processes(self):
        """Print all upload process names."""
        for p in self.processes():
            if 'upload' in p['category']:
                print(p['name'])

    def print_process_inputs(self, process_name):
        """Print process input fields and types.

        :param process_name: Process object name
        :type process_name: string

        """
        p = self.processes(process_name=process_name)

        if len(p) == 1:
            p = p[0]
        else:
            Exception('Invalid process name')

        for field_schema, _, _ in iterate_schema({}, p['input_schema'], 'input'):
            name = field_schema['name']
            typ = field_schema['type']
            # value = fields[name] if name in fields else None
            print("{} -> {}".format(name, typ))

    def rundata(self, strjson):
        """POST JSON data object to server"""

        d = json.loads(strjson)
        return self.api.data.post(d)

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
            raise ValueError(mgs='data must be dict, str or unicode')

        resource = resource.lower()
        if resource not in ('data', 'collection', 'process', 'trigger', 'template'):
            raise ValueError(mgs='resource must be data, collection, process, trigger or template')

        # if resource == 'collection':
        #     resource = 'case'
        #
        # if resource == 'process':
        #     resource = 'processor'

        # Does it make any sense that someone could post processors? Or tiggers? Or templates?

        url = urlparse.urljoin(self.url, '/api/{}'.format(resource))
        return requests.post(url,
                             data=data,
                             auth=self.auth,
                             headers={
                                 'cache-control': 'no-cache',
                                 'content-type': 'application/json',
                                 'accept': 'application/json, text/plain, */*',
                                 'referer': self.url,
                             })

    def upload(self, process_name, name='', descriptor=None, descriptor_schema=None, collections=[], **fields):
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
        proc_name_to_id = dict([(x['name'], x['slug']) for x in self.processes()])

        p = self.processes(process_name=process_name)

        if len(p) == 1:
            p = p[0]
        else:
            Exception('Invalid process name {}'.format(process_name))

        for field_name, field_val in fields.items():
            if field_name not in p['input_schema']:
                Exception("Field {} not in process {} inputs".format(field_name, p['name']))

            if find_field(p['input_schema'], field_name)['type'].startswith('basic:file:'):
                if not os.path.isfile(field_val):
                    Exception("File {} not found".format(field_val))

        inputs = {}

        for field_name, field_val in fields.items():
            if find_field(p['input_schema'], field_name)['type'].startswith('basic:file:'):

                file_temp = self._upload_file(field_val)

                if not file_temp:
                    Exception("Upload failed for {}".format(field_val))

                file_name = ntpath.basename(field_val)
                inputs[field_name] = {
                    'file': file_name,
                    'file_temp': file_temp
                }
            else:
                inputs[field_name] = field_val

        d = {
            'status': 'uploading',  # should it be uploaded?
            'process': proc_name_to_id[process_name],
            'input': inputs,
            'slug': str(uuid.uuid4()),
            'name': name,
        }

        if descriptor:
            d['descriptor'] = descriptor

        if descriptor_schema:
            d['descriptor_schema'] = descriptor_schema

        if len(collections) > 0:
            d['collections'] = collections

        return self.create(d)

    def _upload_file(self, fn):
        """Upload a single file on the platform.

        File is uploaded in chunks of 1,024 bytes.

        :param fn: File path
        :type fn: string

        """
        file_size = os.path.getsize(fn)
        chunk_number = 0
        base_name = os.path.basename(fn)
        session_id = str(uuid.uuid4())

        response = None
        with open(fn, 'rb') as f:
            while True:
                chunk = f.read(CHUNK_SIZE)
                if not chunk:
                    break

                for i in range(5):
                    if i > 0 and response is not None:
                        print("Chunk upload failed (error {}): repeating for chunk number {} ."
                              .format(response.status_code, chunk_number))

                    response = requests.post(urlparse.urljoin(self.url, 'upload/'),
                                             auth=self.auth,

                                            # request are smart and make
                                            #  'CONTENT_TYPE': 'multipart/form-data;''
                                             files={'file':(base_name, chunk)},

                                             # stuff in data will be present in response.POST on server
                                             data={
                                                '_chunkSize': CHUNK_SIZE,
                                                '_totalSize': file_size,
                                                '_chunkNumber': chunk_number,
                                                '_currentChunkSize': len(chunk),
                                            },
                                             headers={
                                                 'Session-Id': session_id}
                                            )
                    if response.status_code in [200, 201]:
                        break
                else:
                    # Upload of a chunk failed (5 retries)
                    return None

                progress = 100. * (chunk_number * CHUNK_SIZE + len(chunk)) / file_size
                sys.stdout.write("\n{:.0f} % Uploaded {}".format(progress, fn))
                sys.stdout.flush()
                chunk_number += 1
        print()
        return response.json()['files'][0]['temp']

    def download(self, data_objects, field):
        """Download files of data objects.

        :param data_objects: Data object ids
        :type data_objects: list of UUID strings
        :param field: Download field name
        :type field: string
        :rtype: generator of requests.Response objects

        """
        if not field.startswith('output'):
            raise ValueError("Only process results (output.* fields) can be downloaded")

        for o in data_objects:
            o = str(o)
            if re.match('^[0-9a-fA-F]{24}$', o) is None:
                raise ValueError("Invalid object id {}".format(o))

            if o not in self.cache['objects']:
                self.cache['objects'][o] = Data(self.ta(o).get(), self)

            if field not in self.cache['objects'][o].annotation:
                raise ValueError("Download field {} does not exist".format(field))

            ann = self.cache['objects'][o].annotation[field]
            if ann['type'] != 'basic:file:':
                raise ValueError("Only basic:file: field can be downloaded")

        for o in data_objects:
            ann = self.cache['objects'][o].annotation[field]
            url = urlparse.urljoin(self.url, 'data/{}/{}'.format(o, ann['value']['file']))
            yield requests.get(url, stream=True, auth=self.auth)


class ResAuth(requests.auth.AuthBase):

    """
    Attach HTTP Resolwe Authentication to Request object.

    __init__ se pozene samo tkrat ko ustvaris ta objekt
    __call__ se pa pozene vsakic ko ustvarjeni objekt poklices! Torej vedno razen prvic? tudi prvic?

    """

    def __init__(self, email=DEFAULT_EMAIL, password=DEFAULT_PASSWD, url=DEFAULT_URL):
        payload = {
            'username': email,
            'password': password
        }

        try:
            response = requests.post(urlparse.urljoin(url, '/rest-auth/login/'), data=payload)
        except requests.exceptions.ConnectionError:
            raise Exception('Server not accessible on {}'.format(url))

        if response.status_code == 403:
            raise Exception('Invalid credentials.')

        if not ('sessionid' in response.cookies and 'csrftoken' in response.cookies):
            raise Exception('Invalid credentials.')

        self.sessionid = response.cookies['sessionid']
        self.csrftoken = response.cookies['csrftoken']
        # self.subscribe_id = str(uuid.uuid4())

    def __call__(self, request):
        # modify and return the request
        request.headers['Cookie'] = 'csrftoken={}; sessionid={}'.format(self.csrftoken, self.sessionid)
        request.headers['X-CSRFToken'] = self.csrftoken

        # Not needed until we support HTTP Push with the API
        # if r.path_url != '/upload/':
        #     r.headers['X-SubscribeID'] = self.subscribe_id
        return request
