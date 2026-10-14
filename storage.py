import os

import boto3
import psycopg
from dotenv import load_dotenv

load_dotenv()

BUCKET = "assets"


def get_db() -> psycopg.Connection:
    return psycopg.connect(os.environ["DATABASE_URL"])


def get_bucket_client():
    return boto3.client("s3")
