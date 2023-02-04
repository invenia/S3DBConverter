import io
import json
import os
from urllib.parse import unquote

from loguru import logger

from lambdas.common import SOURCE_BUCKET, convert_data, s3_multi_p_upload


def lambda_handler(event, context):
    """The Request Handler Function
    Runs the file format conversion jobs generated by the Request Generator
    Function (backfills) or Prod Listener Function (live). There are currently two
    types of requests:
    - Single file requests: Converts a single source file into a single dest file. The
      payload countains a single source s3 key.
    - Batch file requests: Merges multiple source files and converts them into a single
      dest file. The payload countains multiple source s3 key.

    Note that this code is shared by both the single-request and batch-reqeust lambda
    functions, using 2 separate lambda functions for different memory requirements.
    """
    logger.info(event)

    for message in event["Records"]:
        event = json.loads(unquote(message["body"]))

        compression = event["compression"]
        level = event.get("compression_level")
        dest_prefix = event["dest_prefix"]
        dest_store = event["dest_store"]
        partition_size = event["partition_size"]
        file_format = event["file_format"]

        # live events
        if "s3_key" in event:
            s3keys = [event["s3_key"]]

        # backfill requests
        else:
            s3key_prefix = event["s3key_prefix"]
            s3key_suffixes = event["s3key_suffixes"]
            s3keys = [os.path.join(s3key_prefix, i) for i in s3key_suffixes]

        for dest_key, data in convert_data(
            s3keys,
            dest_prefix,
            dest_store,
            partition_size,
            file_format,
            compression,
            level=level,
        ):
            logger.info(f"Uploading file '{dest_key}'...")
            s3_multi_p_upload(SOURCE_BUCKET, dest_key, io.BytesIO(data))
