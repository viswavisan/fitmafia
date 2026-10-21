import os
import oci
from oci.object_storage import ObjectStorageClient

class ObjectStorageManager:
    def __init__(self):
        self.CONFIG = {
            "user": os.getenv("user"),
            "fingerprint": os.getenv("fingerprint"),
            "tenancy": os.getenv("tenancy"),
            "region": os.getenv("region"),
            "key_file": os.getenv("key_file"),
            "namespace": os.getenv("namespace"),
            "bucket_name": os.getenv("bucket_name"),
        }
        self.object_storage_client = ObjectStorageClient(self.CONFIG)

    def upload_file(self, file_storage, filename):
        try:
            self.object_storage_client.put_object(
                namespace_name=self.CONFIG["namespace"],
                bucket_name=self.CONFIG["bucket_name"],
                object_name=filename,
                put_object_body=file_storage.stream,
                content_type=file_storage.content_type
            )
            return f"https://objectstorage.{self.CONFIG['region']}.oraclecloud.com/n/{self.CONFIG['namespace']}/b/{self.CONFIG['bucket_name']}/o/{filename}"

        except Exception as e:
            return f"Error uploading to object storage: {e}"

    def get_file_url(self, object_name):
        if not object_name:
            return None
        return f"https://objectstorage.{self.CONFIG['region']}.oraclecloud.com/n/{self.CONFIG['namespace']}/b/{self.CONFIG['bucket_name']}/o/{object_name}"

    def list_objects(self, prefix=""):
        try:
            response = self.object_storage_client.list_objects(
                namespace_name=self.CONFIG["namespace"],
                bucket_name=self.CONFIG["bucket_name"],
                prefix=prefix
            )
            return response.data.objects
        except Exception as e:
            print(f"Error listing objects: {e}")
            return []