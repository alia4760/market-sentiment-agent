import os
from datetime import date, datetime, timezone

import boto3
import psycopg
from dotenv import load_dotenv

load_dotenv()

BUCKET = "assets"


def get_db() -> psycopg.Connection:
    return psycopg.connect(os.environ["DATABASE_URL"])


def get_bucket_client():
    return boto3.client("s3")


def today() -> date:
    return datetime.now(timezone.utc).date()


def to_int(value) -> int | None:
    return int(value) if value is not None else None
