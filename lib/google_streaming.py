from google.cloud import storage
from google.cloud.storage.blob import Blob
from google.cloud.exceptions import NotFound
import os


class GoogleStorageUploader(object):
    """Client to bundle configuration needed for API requests.

        :type bucket: str
        :param bucket: Name of the bucket, which will be used for upload

        :type project: str or None
        :param project: the project which the client acts on behalf of. Will be
                        passed when creating a topic.  If not passed,
                        falls back to the default inferred from the environment.

        :type credentials: :class:`~google.auth.credentials.Credentials`
        :param credentials: (Optional) The OAuth2 Credentials to use for this
                            client. If not passed (and if no ``_http`` object is
                            passed), falls back to the default inferred from the
                            environment.

        :type _http: :class:`~requests.Session`
        :param _http: (Optional) HTTP object to make requests. Can be any object
                      that defines ``request()`` with the same interface as
                      :meth:`requests.Session.request`. If not passed, an
                      ``_http`` object is created that is bound to the
                      ``credentials`` for the current object.
                      This parameter should be considered private, and could
                      change in the future.

        :type delete_old: bool
        :param delete_old: Delete old bucket at first and recreate new one
        """

    def __init__(self, bucket: str, project=None, credentials=None, _http=None, delete_old=False):
        self.client = storage.Client(project, credentials, _http)
        self.bucket = bucket
        self.__check_bucket(delete_old)

    def __check_bucket(self, delete_old=False):
        self.bucket_object = self.client.bucket(self.bucket)
        if not self.bucket_object.exists():
            self.__create_bucket()
        elif delete_old:
            self.__delete_old()
            self.__create_bucket()

    def __create_bucket(self):
        self.bucket_object.lifecycle_rules = [{
            'action': {'type': 'Delete'},
            'condition': {'age': 1},
        }]
        self.bucket_object.create()

    def __delete_old(self):
        self.bucket_object.delete()

    def upload_file(self, file_path: str):
        """
        :param file_path: path to the file
        :rtype: :class:`google.cloud.storage.blob.Blob`
        :returns: The blob object created.
        """
        basename = os.path.basename(file_path)
        full_path = os.path.abspath(file_path)

        # with open(full_path) as file_object:
        blob = self.bucket_object.blob(basename)
        if not blob.exists():
            blob.upload_from_filename(full_path)

        return blob

    def delete_file(self, blob: Blob):
        try:
            blob.delete()
        except NotFound:
            return False
