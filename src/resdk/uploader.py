"""The uploader class.

Supports uploading to S3 bucket and to Genialis server.
"""

import uuid
from enum import Enum, auto
from pathlib import Path
from typing import TYPE_CHECKING, Optional, Union
from urllib.parse import urljoin

import boto3
import botocore
import tqdm
from mypy_boto3_s3 import S3Client

from resdk.aws.session import get_refreshable_boto3_session
from resdk.constants import CHUNK_SIZE
from resdk.exceptions import ResolweServerError

if TYPE_CHECKING:
    from resdk.resolwe import Resolwe


class UploadType(Enum):
    """Supported uploader types."""

    LOCAL = auto()
    S3 = auto()

    @staticmethod
    def default() -> "UploadType":
        """Return the default upload type."""
        return UploadType.LOCAL


class ProgressCallback:
    """Show progress during upload/download."""

    def __init__(self, progress_bar: tqdm.tqdm):
        """Store the reference to the progress bar.

        The user is responsible to create the progress bar and setting the total amount
        of bytes to transfer on it.
        """
        self._progress_bar = progress_bar

    def __call__(self, transfered_bytes: int):
        """Update the progress bar with transfered bytes."""
        self._progress_bar.update(transfered_bytes)


class Uploader:
    """Upload files to the Genialis platform.

    It supports uploading files to the server and directly to the S3 bucket.
    """

    def __init__(self, resolwe: "Resolwe"):
        """Initialize the uploader instance."""
        self.resolwe = resolwe
        self.upload_methods = {
            UploadType.LOCAL: self._upload_local,
            UploadType.S3: self._upload_s3,
        }
        self._boto_session: Optional[boto3.Session] = None
        self._upload_config: Optional[dict] = None

    def invalidate_cache(self):
        """Remove local cache for upload configuration."""
        self._upload_config = None

    @property
    def upload_config(self) -> dict:
        """Get the upload configuration.

        If configuration can not be read from the server the default
        configuration with default upload type is returned.

        Use cached version if available.
        """
        if self._upload_config is None:
            try:
                self._upload_config = self.resolwe.api.upload_config.get()
            except ResolweServerError:
                self.resolwe.logger.exception("Upload config could not be retrieved.")
                self._upload_config = {"type": UploadType.default().name}
        return self._upload_config

    @property
    def upload_type(self) -> UploadType:
        """Get the current upload type.

        When type in the configuration is not known the default upload type is
        returned.
        """
        try:
            return UploadType[self.upload_config["type"]]
        except KeyError:
            self.resolwe.logger.exception("Received unknown upload type.")
            return UploadType.default()

    def upload(self, file_path: Union[Path, str]) -> str:
        """Upload the given file to the platform.

        :attr file_path: file path

        :returns: the URI of the uploaded file.
        """
        return self.upload_methods[self.upload_type](file_path)

    @property
    def _s3_client(self) -> S3Client:
        """Get and return the S3 client."""
        if self._boto_session is None:
            credentials = self._refresh_credentials_metadata(
                self.upload_config["config"]["credentials"]
            )
            region = self.upload_config["config"]["region"]
            self._boto_session = get_refreshable_boto3_session(
                credentials, self._refresh_credentials_metadata, region
            )

        return self._boto_session.client(
            "s3", config=botocore.client.Config(signature_version="s3v4")
        )

    def _refresh_credentials_metadata(
        self, credentials: Optional[dict] = None
    ) -> dict[str, str]:
        """Create dictionary necessary to refresh credentials.

        The credentials (if not given) are obtained by querying the upload
        configuration. They must be dictionary with the following keys:
        - AccessKeyId
        - SecretAccessKey
        - SessionToken
        - Expiration.

        :raises KeyError: when credentials are not in the correct format.
        """
        credentials = (
            credentials or self.resolwe.api.upload_config.get()["config"]["credentials"]
        )
        return {
            "access_key": credentials["AccessKeyId"],
            "secret_key": credentials["SecretAccessKey"],
            "token": credentials["SessionToken"],
            "expiry_time": credentials["Expiration"],
        }

    def _upload_s3(self, file_path: Union[Path, str], show_progress=True) -> str:
        """Upload the given file in the S3 bucket.

        :attr file_path: file path.

        :returns: the presigned URL that can be used to download the file.
        """
        prefix = str(self.upload_config["config"]["prefix"])
        bucket_name = self.upload_config["config"]["bucket_name"]

        destination = Path(prefix) / str(uuid.uuid4())
        # Use progress bar to show progress.
        with tqdm.tqdm(
            total=Path(file_path).stat().st_size,
            disable=not show_progress,
            desc=f"Uploading file {file_path}",
        ) as progress_bar:
            self._s3_client.upload_file(
                Filename=str(file_path),
                Key=destination.as_posix(),
                Bucket=bucket_name,
                Callback=ProgressCallback(progress_bar),
            )
        return f"s3://{bucket_name}/{destination.as_posix()}"

    def _upload_local(self, file_path: Union[Path, str], show_progress=True):
        """Upload the given file to the server.

        File is uploaded in chunks of size CHUNK_SIZE bytes.

        :attr file_path: file path.

        :raises RuntimeError: when session is None.
        """
        response = None
        chunk_number = 0
        session_id = str(uuid.uuid4())
        file_uid = str(uuid.uuid4())
        file_path = Path(file_path)
        file_size = file_path.stat().st_size
        base_name = file_path.name

        # Check that session (can be None) is set.
        if self.resolwe.session is None:
            raise RuntimeError("Session has not been initialized.")

        with (
            file_path.open("rb") as file_,
            tqdm.tqdm(
                total=file_size,
                disable=not show_progress,
                desc=f"Uploading file {file_path}",
            ) as progress_bar,
        ):
            while True:
                chunk = file_.read(CHUNK_SIZE)
                if not chunk:
                    break

                for i in range(5):
                    if i > 0 and response is not None:
                        self.resolwe.logger.warning(
                            "Chunk upload failed (error %s): repeating for chunk number %s",
                            response.status_code,
                            chunk_number,
                        )

                    response = self.resolwe.session.post(
                        urljoin(self.resolwe.url, "upload/"),
                        auth=self.resolwe.auth,
                        # request are smart and make
                        # 'CONTENT_TYPE': 'multipart/form-data;''
                        files={"file": (base_name, chunk)},
                        # stuff in data will be in response.POST on server
                        data={
                            "_chunkSize": CHUNK_SIZE,
                            "_totalSize": file_size,
                            "_chunkNumber": chunk_number,
                            "_currentChunkSize": len(chunk),
                        },
                        headers={"Session-Id": session_id, "X-File-Uid": file_uid},
                    )

                    if response.status_code in [200, 201]:
                        break
                else:
                    # Upload of a chunk failed (5 retries)
                    return None

                progress_bar.update(len(chunk))
                chunk_number += 1

        return response.json()["files"][0]["temp"]
