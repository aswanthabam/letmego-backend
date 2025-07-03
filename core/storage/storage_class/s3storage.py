import io
from typing import Union
from fastapi import UploadFile
import boto3
from core.storage.storage_class.abstract import Storage


class S3Storage(Storage):
    def __init__(
        self,
        bucket_name: str,
        aws_access_key_id: str,
        aws_secret_access_key: str,
        region_name: str,
        base_path: str = "",
        private: bool = False,
    ):
        """
        Initialize the S3Storage.

        Args:
            bucket_name (str): Name of the S3 bucket.
            aws_access_key_id (str): AWS access key.
            aws_secret_access_key (str): AWS secret key.
            region_name (str): AWS region.
            base_path (str): Prefix path in the bucket (optional).
        """
        super().__init__(volume=bucket_name, base_path=base_path)
        self.bucket_name = bucket_name
        self.base_path = base_path.strip("/")
        self.s3_client = boto3.client(
            "s3",
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=region_name,
        )
        self.private = private

    def save(
        self,
        content: bytes,
        filepath: str,
        content_type: str | None = None,
        *args,
        **kwargs,
    ) -> str:
        """
        Synchronously uploads a file to S3.

        Args:
            content (UploadFile | BytesIO | bytes): File content to upload.
            filepath (str): Relative path (key) in the S3 bucket.
            content_type (str | None): MIME type (optional).

        Returns:
            str: The full S3 object key.

        Raises:
            IOError: If the upload fails.
        """
        if self.base_path.endswith("/"):
            self.base_path = self.base_path[:-1]
        if filepath.startswith("/"):
            filepath = filepath[1:]
        if filepath.endswith("/"):
            filepath = filepath[:-1]

        s3_key = f"{self.base_path}/{filepath}" if self.base_path else filepath

        try:
            content = self._get_bytes(content)

            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=content,
                ContentType=content_type or "application/octet-stream",
            )

            return s3_key

        except Exception as e:
            raise IOError(f"Failed to upload file to S3 at {s3_key}: {e}")

    def get_path(self, filepath):
        """
        Get the full S3 object key.

        Args:
            filepath (str): Relative path in the S3 bucket.

        Returns:
            str: The full S3 object key.
        """
        if self.base_path.endswith("/"):
            self.base_path = self.base_path[:-1]
        if filepath.startswith("/"):
            filepath = filepath[1:]
        if filepath.endswith("/"):
            filepath = filepath[:-1]

        return f"{self.base_path}/{filepath}" if self.base_path else filepath

    def get_url(self, filepath):
        """
        Get the URL for a file stored in S3.
        """
        s3_key = self.get_path(filepath)
        try:
            url = self.s3_client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket_name, "Key": s3_key},
                ExpiresIn=3600,  # URL valid for 1 hour
            )
            return url
        except Exception as e:
            raise IOError(f"Failed to generate URL for S3 object {s3_key}: {e}")
