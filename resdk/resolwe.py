""".. Ignore pydocstyle D400.

=======
Resolwe
=======

.. autoclass:: resdk.Resolwe
   :members:

"""
from __future__ import absolute_import, division, print_function

import copy
import logging
import ntpath
import os
import re
import subprocess
import uuid

import requests
import slumber
import yaml
# Needed because we mock requests in test_resolwe.py
from requests.exceptions import ConnectionError  # pylint: disable=redefined-builtin
from six.moves.urllib.parse import urljoin  # pylint: disable=import-error

from .exceptions import ValidationError, handle_http_exception
from .query import ResolweQuery
from .resources import Collection, Data, Process, Relation, Sample
from .resources.kb import Feature, Mapping
from .resources.utils import (
    endswith_colon, get_collection_id, get_data_id, iterate_fields, iterate_schema,
)

CHUNK_SIZE = 8000000  # 8MB
DEFAULT_URL = 'http://localhost:8000'
# Tools directory on the Resolwe server, for example:
# username@torta.bcmt.bcm.edu://genialis/tools
TOOLS_REMOTE_HOST = os.environ.get('TOOLS_REMOTE_HOST', None)


def version_str_to_tuple(version):
    """Split version string to tuple of integers."""
    return tuple(map(int, (version.split("."))))


def version_tuple_to_str(version):
    """Join version tuple to string."""
    return '.'.join(map(str, version))


class ResolweResource(slumber.Resource):
    """Wrapper around slumber's Resource with custom exceptions handler."""

    def __getattribute__(self, item):
        """Return class attribute and wrapp request methods in exception handler."""
        attr = super(ResolweResource, self).__getattribute__(item)
        if item in ['get', 'options', 'head', 'post', 'patch', 'put', 'delete']:
            return handle_http_exception(attr)
        return attr


class ResolweAPI(slumber.API):
    """Use custom ResolweResource resource class in slumber's API."""

    resource_class = ResolweResource


class Resolwe(object):
    """Connect to a Resolwe server.

    :param email: user's email
    :type email: str
    :param password: user's password
    :type password: str
    :param url: Resolwe server instance
    :type url: str

    """

    def __init__(self, username=None, password=None, url=None):
        """Initialize attributes."""
        if url is None:
            # Try to get URL from environmental variable, otherwise fallback to default.
            url = os.environ.get('RESOLWE_HOST_URL', DEFAULT_URL)
            # TODO: Remove this
            if 'RESOLWE_HOST_URL' not in os.environ:
                url = os.environ.get('RESOLWE_API_HOST', url)

        if username is None:
            username = os.environ.get('RESOLWE_API_USERNAME', None)

        if password is None:
            password = os.environ.get('RESOLWE_API_PASSWORD', None)

        self.url = url
        self.auth = ResAuth(username, password, url)
        self.api = ResolweAPI(urljoin(url, '/api/'), self.auth, append_slash=False)

        self.data = ResolweQuery(self, Data)
        self.collection = ResolweQuery(self, Collection)
        self.sample = ResolweQuery(self, Sample)
        self.relation = ResolweQuery(self, Relation)
        self.process = ResolweQuery(self, Process)
        self.feature = ResolweQuery(self, Feature)
        self.mapping = ResolweQuery(self, Mapping)

        self.logger = logging.getLogger(__name__)

    def __repr__(self):
        """Return string representation of the current object."""
        if self.auth.username:
            return "Resolwe <url: {}, username: {}>".format(self.url, self.auth.username)
        return "Resolwe <url: {}>".format(self.url)

    def _register(self, src, slug):
        """Register processes on the server.

        :param src: Register process from source YAML file
        :type src: str
        :param slug: Process slug (unique identifier)
        :type slug: str

        """
        if not os.path.isfile(src):
            raise ValueError("File not found: {}.".format(src))

        processes = []

        try:
            with open(src) as src_file:
                processes = yaml.load(src_file)

        except yaml.parser.ParserError:
            raise

        process = None
        for process in processes:
            if process.get('slug', None) == slug:
                break
        else:
            raise ValueError("Process source given '{}' but process "
                             "slug not found: '{}'.".format(src, slug))

        endswith_colon(process, 'type')
        endswith_colon(process, 'category')

        for field in ['input', 'output']:
            if field in process:
                for schema, _, _ in iterate_schema({}, process[field], field):
                    endswith_colon(schema, 'type')

            process['{}_schema'.format(field)] = process.pop(field)

        if 'persistence' in process:
            persistence_map = {'RAW': 'RAW', 'CACHED': 'CAC',
                               'CAC': 'CAC', 'TEMP': 'TMP', 'TMP': 'TMP'}
            process['persistence'] = persistence_map[process['persistence']]

        try:
            server_process = self.process.filter(slug=process['slug'], ordering='-version')[:1]

            if len(server_process) == 1:
                server_process = server_process[0]
                # Version for newly reistered process has to be increased. If
                # this has not been already done in yaml file it is raised now.
                process_version = version_str_to_tuple(process['version'])
                server_version = version_str_to_tuple(server_process.version)
                if process_version <= server_version:
                    new_process_version = server_version[:-1] + (server_version[-1] + 1,)
                    process['version'] = version_tuple_to_str(new_process_version)
                    self.logger.warning(
                        "Process '%s' version increased automatically: %s",
                        slug, process['version']
                    )

            response = self.api.process.post(process)

        # Updating processes is supported only on development servers
        # This error will be raised on production server.
        except slumber.exceptions.HttpClientError as http_client_error:
            if http_client_error.response.status_code == 405:  # pylint: disable=no-member
                self.logger.warning("Server does not support adding processes")
            raise

        return response

    def _upload_tools(self, tools):
        """Upload auxiliary scripts to Resolwe server.

        Upload auxiliary script files (tools to call in the processes)
        to the Resolwe server's runtime Docker container.

        :param tools: Process auxiliary scripts
        :type tools: list of str

        :rtype: None

        """
        if TOOLS_REMOTE_HOST is None:
            raise ValueError("Define TOOLS_REMOTE_HOST environmental variable")

        self.logger.info("SCP: %s", TOOLS_REMOTE_HOST)
        for tool in tools:
            if not os.path.isfile(tool):
                raise ValueError("Tools file not found: '{}'.".format(tool))
            # Define subprocess, but not yet run it. Also:
            # (1) redirect stderr to stdout
            # (2) enable to retrieve stdout of the subprocess in here
            sub_process = subprocess.Popen(
                'scp -r {} {}'.format(tool, TOOLS_REMOTE_HOST),
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT)
            # Run the subprocess:
            stdout, _ = sub_process.communicate()
            self.logger.info(stdout)
            if sub_process.returncode == 1:
                raise ValueError("Something wrong while SCP for tool: '{}'.".format(tool))
            if sub_process.returncode > 1:
                self.logger.warning("STATUS: %s", sub_process.returncode)

    def _process_file_field(self, path):
        """Process file field and return it in resolwe-specific format.

        Upload referenced file if it is stored locally and return
        original filename and it's temporary location.

        :param path: path to file (local or url)
        :type path: str/path

        :rtype: dict
        """
        url_regex = r'^(https?|ftp)://[-A-Za-z0-9\+&@#/%?=~_|!:,.;]*[-A-Za-z0-9\+&@#/%=~_|]$'
        if re.match(url_regex, path):
            file_name = path.split('/')[-1].split('#')[0].split('?')[0]
            return {
                'file': file_name,
                'file_temp': path
            }

        if not os.path.isfile(path):
            raise ValueError("File {} not found.".format(path))

        file_temp = self._upload_file(path)

        if not file_temp:
            raise Exception("Upload failed for {}.".format(path))

        file_name = ntpath.basename(path)
        return {
            'file': file_name,
            'file_temp': file_temp,
        }

    def _get_process(self, slug=None):
        """Return process with given slug.

        Raise error if process doesn't exist or more than one is returned.
        """
        return self.process.get(slug=slug, ordering='-version', limit=1)

    def _process_inputs(self, inputs, process):
        """Process input fields.

        Processing includes:
        * wrapping ``list:*`` to the list if they are not already
        * dehydrating values of ``data:*`` and ``list:data:*`` fields
        * uploading files in ``basic:file:`` and ``list:basic:file:``
          fields
        """
        inputs = copy.deepcopy(inputs)  # leave original intact

        try:
            for schema, fields in iterate_fields(inputs, process.input_schema):
                field_name = schema['name']
                field_type = schema['type']
                field_value = fields[field_name]

                # XXX: Remove this when supported on server.
                # Wrap `list:` fields into list if they are not already
                if field_type.startswith('list:') and not isinstance(field_value, list):
                    fields[field_name] = [field_value]
                    field_value = fields[field_name]  # update value for the rest of the loop

                # Dehydrate `data:*` fields
                if field_type.startswith('data:'):
                    fields[field_name] = get_data_id(field_value)

                # Dehydrate `list:data:*` fields
                elif field_type.startswith('list:data:'):
                    fields[field_name] = [get_data_id(data) for data in field_value]

                # Upload files in `basic:file:` fields
                elif field_type == 'basic:file:':
                    fields[field_name] = self._process_file_field(field_value)

                # Upload files in list:basic:file:` fields
                elif field_type == 'list:basic:file:':
                    fields[field_name] = [self._process_file_field(obj) for obj in field_value]

        except KeyError as key_error:
            field_name = key_error.args[0]
            slug = process.slug
            raise ValidationError(
                "Field '{}' not in process '{}' input schema.".format(field_name, slug))

        return inputs

    def run(self, slug=None, input={}, descriptor=None,  # pylint: disable=redefined-builtin
            descriptor_schema=None, collections=[],
            data_name='', src=None, tools=None):
        """Run process and return the corresponding Data object.

        1. Upload files referenced in inputs
        2. Create Data object with given inputs
        3. Command is run that processes inputs into outputs
        4. Return Data object

        The processing runs asynchronously, so the returned Data
        object does not have an OK status or outputs when returned.
        Use data.update() to refresh the Data resource object.

        For process development, use src and tools arguments. If src
        argument given, a process from the specified source YAML file
        is first uploaded and registered on the server. List the
        process auxiliary scripts (tools to call in the processes)
        in the tools argument. This scripts will be copied to the
        server automatically with SCP.

        :param str slug: Process slug (human readable unique identifier)
        :param dict input: Input values
        :param dict descriptor: Descriptor values
        :param str descriptor_schema: A valid descriptor schema slug
        :param list collections: Id's of collections into which data object should be included
        :param str data_name: Default name of data object
        :param str src: Path to YAML file with custom process definition
        :param list tools: Paths to auxiliary scripts to upload

        :return: data object that was just created
        :rtype: Data object
        """
        if ((descriptor and not descriptor_schema) or
                (not descriptor and descriptor_schema)):
            raise ValueError("Set both or neither descriptor and descriptor_schema.")

        if src is not None:
            self._register(src, slug)

        if tools is not None:
            self._upload_tools(tools)

        process = self._get_process(slug)
        inputs = self._process_inputs(input, process)

        # Dehydrate `collections` list
        dehydrated_collections = []
        for collection in collections:
            dehydrated_collections.append(get_collection_id(collection))
        collections = dehydrated_collections

        data = {
            'process': process.slug,
            'input': inputs,
        }

        if data_name:
            data['name'] = data_name

        if descriptor and descriptor_schema:
            data['descriptor'] = descriptor
            data['descriptor_schema'] = descriptor_schema

        if collections:
            data['collections'] = collections

        model_data = self.api.data.post(data)
        return Data(model_data=model_data, resolwe=self)

    def get_or_run(self, slug=None, input={}):  # pylint: disable=redefined-builtin
        """Return existing object if found, otherwise create new one.

        :param str slug: Process slug (human readable unique identifier)
        :param dict input: Input values
        """
        process = self._get_process(slug)
        inputs = self._process_inputs(input, process)

        data = {
            'process': process.slug,
            'input': inputs,
        }

        model_data = self.api.data.get_or_create.post(data)
        return Data(model_data=model_data, resolwe=self)

    def _upload_file(self, file_path):
        """Upload a single file on the platform.

        File is uploaded in chunks of size CHUNK_SIZE bytes.

        :param str file_path: File path

        """
        response = None
        chunk_number = 0
        session_id = str(uuid.uuid4())
        file_uid = str(uuid.uuid4())
        file_size = os.path.getsize(file_path)
        base_name = os.path.basename(file_path)

        with open(file_path, 'rb') as file_:
            while True:
                chunk = file_.read(CHUNK_SIZE)
                if not chunk:
                    break

                for i in range(5):
                    if i > 0 and response is not None:
                        self.logger.warning(
                            "Chunk upload failed (error %s): repeating for chunk number %s",
                            response.status_code,
                            chunk_number)

                    response = requests.post(
                        urljoin(self.url, 'upload/'),
                        auth=self.auth,

                        # request are smart and make
                        # 'CONTENT_TYPE': 'multipart/form-data;''
                        files={'file': (base_name, chunk)},

                        # stuff in data will be in response.POST on server
                        data={
                            '_chunkSize': CHUNK_SIZE,
                            '_totalSize': file_size,
                            '_chunkNumber': chunk_number,
                            '_currentChunkSize': len(chunk)},
                        headers={
                            'Session-Id': session_id,
                            'X-File-Uid': file_uid}
                    )

                    if response.status_code in [200, 201]:
                        break
                else:
                    # Upload of a chunk failed (5 retries)
                    return None

                progress = 100. * (chunk_number * CHUNK_SIZE + len(chunk)) / file_size
                message = "{:.0f} % Uploaded {}".format(progress, file_path)
                self.logger.info(message)
                chunk_number += 1

        return response.json()['files'][0]['temp']

    def _download_files(self, files, download_dir=None):  # pylint: disable=redefined-builtin
        """Download files.

        Download files from the Resolwe server to the download
        directory (defaults to the current working directory).

        :param files: files to download
        :type files: list of file URI
        :param download_dir: download directory
        :type download_dir: string
        :rtype: None

        """
        if not download_dir:
            download_dir = os.getcwd()

        if not os.path.isdir(download_dir):
            raise ValueError("Download directory does not exist: {}".format(download_dir))

        if not files:
            self.logger.info("No files to download.")

        else:
            self.logger.info("Downloading files to %s:", download_dir)

            for file_uri in files:
                file_name = os.path.basename(file_uri)
                file_path = os.path.dirname(file_uri)
                file_url = urljoin(self.url, 'data/{}'.format(file_uri))

                # Remove data id from path
                file_path = file_path.split('/', 1)[1] if '/' in file_path else ''
                full_path = os.path.join(download_dir, file_path)
                if not os.path.isdir(full_path):
                    os.makedirs(full_path)

                self.logger.info("* %s", os.path.join(file_path, file_name))

                with open(os.path.join(download_dir, file_path, file_name), 'wb') as file_handle:
                    response = requests.get(file_url, stream=True, auth=self.auth)

                    if not response.ok:
                        response.raise_for_status()
                    else:
                        for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                            file_handle.write(chunk)


class ResAuth(requests.auth.AuthBase):
    """HTTP Resolwe Authentication for Request object.

    :param str username: user's username
    :param str password: user's password
    :param str url: Resolwe server address

    """

    #: Session ID used in HTTP requests
    sessionid = None
    #: CSRF token used in HTTP requests
    csrftoken = None

    def __init__(self, username=None, password=None, url=DEFAULT_URL):
        """Authenticate user on Resolwe server."""
        self.logger = logging.getLogger(__name__)

        self.username = username
        self.url = url

        if not username and not password:
            return

        payload = {'username': username, 'password': password}

        try:
            response = requests.post(urljoin(url, '/rest-auth/login/'), data=payload)
        except ConnectionError:
            raise ValueError('Server not accessible on {}. Wrong url?'.format(url))

        status_code = response.status_code
        if status_code in [400, 403]:
            msg = 'Response HTTP status code {}. Invalid credentials?'.format(status_code)
            raise ValueError(msg)

        if not ('sessionid' in response.cookies and 'csrftoken' in response.cookies):
            raise Exception('Missing sessionid or csrftoken. Invalid credentials?')

        self.sessionid = response.cookies['sessionid']
        self.csrftoken = response.cookies['csrftoken']
        self.url = url
        # self.subscribe_id = str(uuid.uuid4())

    def __call__(self, request):
        """Set request headers."""
        if self.sessionid and self.csrftoken:
            request.headers['Cookie'] = 'csrftoken={}; sessionid={}'.format(
                self.csrftoken, self.sessionid)
            request.headers['X-CSRFToken'] = self.csrftoken

        request.headers['referer'] = self.url

        # Not needed until we support HTTP Push with the API
        # if r.path_url != '/upload/':
        #     r.headers['X-SubscribeID'] = self.subscribe_id
        return request
