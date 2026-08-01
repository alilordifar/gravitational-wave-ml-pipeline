"""
S3-only persistence layer for RawSignal objects.

No local cache tier — S3 is both cache and durable store.

Write order matters: .npy uploaded first, .json uploaded LAST.
The .json's existence is treated as the "commit" signal — a crash
mid-upload leaves an orphaned .npy (harmless, gets overwritten on
retry) but never a .json without its matching .npy.
"""

import io
import json
from dataclasses import asdict

import boto3
import numpy as np
from botocore.exceptions import ClientError

from src.utils.s3_paths import npy_key, json_key


class _NumpyScalarEncoder(json.JSONEncoder):
    """
    Converts numpy scalar types (e.g. np.float64, np.int64) to native
    Python types, since these can legitimately end up in RawSignal.extra
    (e.g. a GPS time computed via numpy).

    Anything else non-serializable (ndarray, custom objects, etc.) is
    NOT caught here — it raises TypeError, on purpose. Silent
    stringification would hide bugs; better to fail loudly at upload
    time than lose information silently.
    """

    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        return super().default(obj)  # raises TypeError for anything else


class UnserializableMetadataError(TypeError):
    """Raised when RawSignal.extra (or any field) contains a value
    that cannot be safely converted to JSON."""


class S3Uploader:
    def __init__(self, bucket: str, client=None):
        self.bucket = bucket
        self.client = client or boto3.client("s3")

    def exists_remote(self, asset_key: str) -> bool:
        """Check only the .json key — cheap HEAD, commit-signal semantics."""
        key = json_key(asset_key)
        try:
            self.client.head_object(Bucket=self.bucket, Key=key)
            return True
        except ClientError as e:
            if e.response["Error"]["Code"] in ("404", "NoSuchKey"):
                return False
            raise

    def upload(self, asset_key: str, raw) -> None:
        """
        raw: RawSignal. .data goes to .npy; every other field
        (via dataclasses.asdict) goes to .json.

        Metadata is validated BEFORE any network call — a bad `extra`
        value should never cost you a wasted .npy upload.
        """
        body = self._build_json_body(asset_key, raw)
        self._upload_npy(asset_key, raw.data)
        self._put(json_key(asset_key), body)

    def _build_json_body(self, asset_key: str, raw) -> bytes:
        metadata = asdict(raw)
        metadata.pop("data")  # array goes in .npy, not .json
        try:
            return json.dumps(metadata, cls=_NumpyScalarEncoder).encode("utf-8")
        except TypeError as e:
            raise UnserializableMetadataError(
                f"RawSignal for asset_key={asset_key!r} contains a value that "
                f"cannot be JSON-serialized (check 'extra' dict): {e}"
            ) from e

    def _upload_npy(self, asset_key: str, array: np.ndarray) -> None:
        buf = io.BytesIO()
        np.save(buf, array)
        buf.seek(0)
        self._put(npy_key(asset_key), buf.getvalue())

    def _put(self, key: str, body: bytes) -> None:
        self.client.put_object(Bucket=self.bucket, Key=key, Body=body)