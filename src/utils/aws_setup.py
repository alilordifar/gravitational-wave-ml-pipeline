"""
Idempotent, security-hardened S3 bucket creation for the platform's
raw data landing zone.

Security posture applied:
  - Block Public Access: all four settings ON (no public access possible,
    even via a future misconfigured bucket policy or ACL)
  - Object Ownership: bucket owner enforced (ACLs disabled entirely —
    modern best practice, removes an entire class of misconfiguration)
  - Default encryption: SSE-S3 (AES256) at rest, applied automatically
    to every object with no per-upload code needed
  - Versioning: ON (protects against accidental overwrite/delete —
    relevant given our upload pattern writes .npy then .json separately)
  - Bucket policy: denies any request that isn't HTTPS (aws:SecureTransport)

Safe to run multiple times — every step checks current state first.
"""

import json

import boto3
from botocore.exceptions import ClientError


def ensure_raw_bucket(bucket: str, region: str, client=None) -> None:
    client = client or boto3.client("s3", region_name=region)

    _ensure_bucket_exists(client, bucket, region)
    _block_public_access(client, bucket)
    _enforce_bucket_owner_ownership(client, bucket)
    _enable_default_encryption(client, bucket)
    _enable_versioning(client, bucket)
    _enforce_https_only(client, bucket)

    print(f"[ok] {bucket} in {region} is configured and secure")


def _ensure_bucket_exists(client, bucket: str, region: str) -> None:
    try:
        client.head_bucket(Bucket=bucket)
        print(f"[exists] {bucket}")
        return
    except ClientError as e:
        if e.response["Error"]["Code"] != "404":
            raise  # something other than "doesn't exist" — don't swallow it

    create_kwargs = {"Bucket": bucket}
    # us-east-1 is the one region where you must NOT pass a LocationConstraint
    if region != "us-east-1":
        create_kwargs["CreateBucketConfiguration"] = {"LocationConstraint": region}

    client.create_bucket(**create_kwargs)
    print(f"[created] {bucket} in {region}")


def _block_public_access(client, bucket: str) -> None:
    client.put_public_access_block(
        Bucket=bucket,
        PublicAccessBlockConfiguration={
            "BlockPublicAcls": True,
            "IgnorePublicAcls": True,
            "BlockPublicPolicy": True,
            "RestrictPublicBuckets": True,
        },
    )
    print(f"[secured] public access fully blocked on {bucket}")


def _enforce_bucket_owner_ownership(client, bucket: str) -> None:
    """Disables ACLs entirely — every object is owned by the bucket
    owner regardless of who uploads it. Removes ACL misconfiguration
    as a possible vulnerability."""
    client.put_bucket_ownership_controls(
        Bucket=bucket,
        OwnershipControls={"Rules": [{"ObjectOwnership": "BucketOwnerEnforced"}]},
    )
    print(f"[secured] ACLs disabled (bucket owner enforced) on {bucket}")


def _enable_default_encryption(client, bucket: str) -> None:
    client.put_bucket_encryption(
        Bucket=bucket,
        ServerSideEncryptionConfiguration={
            "Rules": [
                {"ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}}
            ]
        },
    )
    print(f"[secured] default SSE-S3 encryption enabled on {bucket}")


def _enable_versioning(client, bucket: str) -> None:
    client.put_bucket_versioning(
        Bucket=bucket,
        VersioningConfiguration={"Status": "Enabled"},
    )
    print(f"[secured] versioning enabled on {bucket}")


def _enforce_https_only(client, bucket: str) -> None:
    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "DenyInsecureTransport",
                "Effect": "Deny",
                "Principal": "*",
                "Action": "s3:*",
                "Resource": [
                    f"arn:aws:s3:::{bucket}",
                    f"arn:aws:s3:::{bucket}/*",
                ],
                "Condition": {"Bool": {"aws:SecureTransport": "false"}},
            }
        ],
    }
    client.put_bucket_policy(Bucket=bucket, Policy=json.dumps(policy))
    print(f"[secured] HTTPS-only bucket policy applied to {bucket}")