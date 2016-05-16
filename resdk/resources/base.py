"""
Constants and abstract classes.
"""
from __future__ import absolute_import, division, print_function, unicode_literals

import os
import requests
import six

from six.moves.urllib.parse import urljoin  # pylint: disable=import-error


DOWNLOAD_TYPES = {
    'bam': ('data:alignment:bam:', 'output.bam'),
    'exp': ('data:expression:', 'output.exp'),
    'fastq': ('data:reads:fastq:', 'output.fastq'),
}


class BaseResource(object):
    """
    Abstract resource class BaseResource.
    """

    endpoint = None

    def __init__(self, slug=None, id=None,  # pylint: disable=redefined-builtin
                 model_data=None, resolwe=None):
        """
        Abstract resource.

        One and only one of the identifiers (slug, id or model_data)
        should be given.

        :param slug: Resource slug
        :type slug: str
        :param id: Resource ID
        :type id: int
        :param model_data: Resource model data
        :type model_data: dict
        :param resolwe: Resolwe instance
        :type resolwe: Resolwe object

        """
        # Verify that one and only one of slug, id, model_data is given
        identifiers = iter((slug, id, model_data))
        if not any(identifiers) or any(identifiers):
            raise ValueError("One and only one of slug, id or model_data must be given")

        self.id = id  # pylint: disable=invalid-name
        self.slug = slug

        self.api = getattr(resolwe.api, self.endpoint)
        self.resolwe = resolwe

        if id:
            self._update_fields(self.api(id).get())
        elif slug:
            self._update_fields(self.api(id).get())
        elif model_data:
            self._update_fields(model_data)

    def _update_fields(self, fields):
        """
        Update resource fields.

        :param fields: Resource fields
        :type fields: dict

        """
        for field_name, field_value in fields.items():
            setattr(self, field_name, field_value)

    def print_annotation(self):
        """
        Provide annotation data.
        """
        pass

    def files(self, verbose=False):
        """
        Return list of files in resource.
        """
        pass

    def update(self):
        """
        Update resource fields from the server.
        """
        self._update_fields(self.api(self.id).get())

    def download(self, name=None, type=None, download_dir=None, force=False):  # pylint: disable=redefined-builtin
        """
        Download files in resource that match name/type.

        :param name: name of file
        :type name: string
        :param type: (process_type, output_field) or abbreviation for most of such common tuples.
        :type typ: tuple or string
        :param download_dir: download path
        :type download_dir: string
        :param force: if true, download all files regardless of match
        :type force: boolean

        :rtype: None

        Sample usually contains multiple data objects and each data
        object can contain multiple files. Default option is to download
        all of them, but this may not be desired, since some files can be
        rather large. User can provide:

        * name of the desired file (with keyword **name**)
          Only file with corresponding name will be downloaded.
          Example:
          re.sample.get(42).download(name="alignment7.bam")

        or

        * (process_type, output_field) tuple (with keyword **type**)
          In this case only files from output_field from data object
          with process_type will be downloaded.
          Example:
          re.sample.get(42).download(type=('data:alignment:bam:', 'output.bam'))

          For most common types of downloads (bam files,
          expression files, etc.) shortcut notation is provided:

          * 'bam' for BAM files
          * 'exp' for expression files
          * 'fastq' for fastq files

          Example:
          re.sample.get(42).download(type='bam')

        The current working directory is the default download location. With
        download_dir parameter, this can be modified.

        """
        if not download_dir:
            download_dir = os.getcwd()

        # list of all files to download - this list is yet to be
        # filtered by name/type:
        dfiles = self.files(verbose=True)

        if not (name or type) or force:
            pass

        elif name:
            dfiles = [d for d in dfiles if d[1] == name]

        elif type:
            data_type, output_field = None, None
            if isinstance(type, six.string_types) and type in DOWNLOAD_TYPES.keys():
                # type is abbreviation (string)
                data_type, output_field = DOWNLOAD_TYPES[type]
            elif isinstance(type, tuple) and len(type) == 2:
                data_type, output_field = type
            else:
                raise ValueError('Invalid argument type.')
            dfiles = [d for d in dfiles if data_type in d[3] and output_field == d[2]]

        if len(dfiles) == 0:
            print("No files matching.")
            # TODO: "Did you mean..." :-)
        else:
            print("Following files will be downloaded to direcotry {}:".format(download_dir))
            for dfile in dfiles:
                print("* {}".format(dfile[1]))
                # TODO: add file size in print!

            for data_id, filename, _, _ in dfiles:
                with open(os.path.join(download_dir, filename), 'wb') as file_:
                    url = urljoin(self.resolwe.url, 'data/{}/{}'.format(data_id, filename))
                    response = requests.get(url, stream=True, auth=self.resolwe.auth)

                    if not response.ok:
                        response.raise_for_status()
                    else:
                        for chunk in response:
                            file_.write(chunk)

    def __repr__(self):
        return u"{} <id: {}, slug: '{}', name: '{}'>".format(self.__class__.__name__, self.id, self.slug, self.name)  # pylint: disable=no-member
