"""
Constants and abstract classes.
"""
from __future__ import absolute_import, division, print_function, unicode_literals

import os
import six


DOWNLOAD_TYPES = {
    'bam': ('data:alignment:bam:', 'output.bam'),
    'exp': ('data:expression:', 'output.exp'),
    'fastq': ('data:reads:fastq:', 'output.fastq'),
}


class BaseResource(object):
    """
    Abstract class BaseResource.
    """
    endpoint = "BaseResource"

    def __init__(self, resource_data, resolwe):
        """
        Abstract class BaseResource.

        :param resource_data: Annotation data for resource
        :type resource_data: dictionary (JSON from restAPI)
        :param resolwe: Resolwe instance
        :type resolwe: Resolwe object

        :rtype: None
        """
        self.resolwe = resolwe
        self.update(resource_data)

    def update(self, resource_data):
        """
        Update resource annotation.

        :param resource_data: Annotation data for resource
        :type resource_data: dict (JSON from server.)

        :rtype: None
        """
        for field in resource_data:
            setattr(self, field, resource_data[field])

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

    def download(self, name=None, typ=None, download_dir=None, force=False):
        """
        Download files in resource that match name/typ.

        :param name: name of file
        :type name: string
        :param typ: (process_type, output_field) or abbreviation for most of such common tuples.
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

            * (process_type, output_field) tuple (with keyword **typ**)
                In this case only files from output_field from data object
                with process_type will be downloaded.
                Example:
                re.sample.get(42).download(typ=('data:alignment:bam:', 'output.bam'))

                For most common types of downloads (bam files,
                expression files, etc.) shortcut notation is provided:
                    * 'bam' for BAM files
                    * 'exp' for expression files
                    * 'fastq' for fastq files
                Example:
                re.sample.get(42).download(typ='bam')

        The current working directory is the default download location. With
        download_dir parameter, this can be modified.
        """

        if not download_dir:
            download_dir = os.getcwd()

        # list of all files to download - this list is yet to be
        # filtered by name/typ:
        dfiles = self.files(verbose=True)

        if not (name or typ) or force:
            pass

        elif name:
            dfiles = [d for d in dfiles if d[1] == name]

        elif typ:
            data_type, output_field = None, None
            if isinstance(typ, six.string_types):
                # typ is abbreviation (string)
                data_type, output_field = DOWNLOAD_TYPES[typ]
            elif isinstance(typ, tuple) and len(typ) == 2:
                data_type, output_field = typ
            else:
                raise ValueError('Invalid argument typ.')
            dfiles = [d for d in dfiles if data_type in d[3] and output_field == d[2]]

        if len(dfiles) == 0:
            print("No files matching.")
            # TODO: "Did you mean..." :-)
        else:
            print("Following files will be downloaded to direcotry {}:".format(download_dir))
            for dfile in dfiles:
                print("* {}".format(dfile[1]))
                # TODO: add file size in print!

            for data_id, filename, field, _ in dfiles:
                with open(os.path.join(download_dir, filename), 'wb') as file_:
                    handle = self.resolwe.download([data_id], field)
                    for chunk in handle:
                        file_.write(chunk)

    def __repr__(self):
        return u"{}: {} - {}".format(self.endpoint.capitalize(), self.id, self.name)  # pylint: disable=no-member
