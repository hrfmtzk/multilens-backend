import json
import os
import typing
from dataclasses import dataclass
from distutils.util import strtobool
from enum import Enum
from io import SEEK_SET, BytesIO
from uuid import uuid4

import boto3
import sentry_sdk
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.batch import (
    BatchProcessor,
    EventType,
    FailureResponse,
    SuccessResponse,
)
from aws_lambda_powertools.utilities.data_classes.sqs_event import SQSRecord
from aws_lambda_powertools.utilities.typing import LambdaContext
from PIL import Image
from sentry_sdk import capture_exception
from sentry_sdk.integrations.aws_lambda import AwsLambdaIntegration

logger = Logger()
tracer = Tracer()


class Format(Enum):
    JPEG = "jpeg"
    WEBP = "webp"


@dataclass
class ConvertConfig:
    bucket_name: str
    format: typing.Optional[Format] = None
    resize: typing.Optional[int] = None


SENTRY_DSN = os.environ.get("SENTRY_DSN")


if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[AwsLambdaIntegration()],
        traces_sample_rate=1.0,
    )


class SentryBatchProcessor(BatchProcessor):
    def failure_handler(self, record, exception) -> FailureResponse:
        if SENTRY_DSN:
            capture_exception()
        return super().failure_handler(record, exception)


processor = SentryBatchProcessor(event_type=EventType.SQS)


class ImageConvertProcessor:
    def __init__(self, config: ConvertConfig) -> None:
        self.config = config

    def process_records(
        self,
        records: typing.List[typing.Dict[str, typing.Any]],
    ) -> None:
        raise NotImplementedError

    @tracer.capture_method
    def _process_s3_records(
        self, records: typing.List[typing.Dict[str, typing.Any]]
    ) -> None:
        for record in records:
            self._process_s3_record(record)

    @tracer.capture_method
    def _process_s3_record(self, record: typing.Dict[str, typing.Any]) -> None:
        logger.debug(record)
        s3 = boto3.client("s3")

        bucket_name = record["s3"]["bucket"]["name"]
        object_key = record["s3"]["object"]["key"]

        head_response = s3.head_object(Bucket=bucket_name, Key=object_key)
        logger.debug(head_response)
        metadata = head_response["Metadata"]

        with BytesIO() as rbuf:
            s3.download_fileobj(
                Bucket=bucket_name,
                Key=object_key,
                Fileobj=rbuf,
            )
            with Image.open(rbuf) as image, BytesIO() as wbuf:
                if self.config.resize:
                    image.thumbnail((self.config.resize, self.config.resize))
                format = image.format
                if self.config.format:
                    format = self.config.format.value
                if self.config.format == Format.JPEG:
                    image = image.convert("RGB")
                image.save(wbuf, format)
                wbuf.seek(SEEK_SET)
                s3.upload_fileobj(
                    Bucket=self.config.bucket_name,
                    Key="/".join(
                        [
                            (
                                self.config.format.value
                                if self.config.format
                                else "original"
                            ),
                            (
                                str(self.config.resize)
                                if self.config.resize
                                else "original"
                            ),
                            metadata.get("userid", "anonymous"),
                            metadata.get("imageid", str(uuid4())),
                        ]
                    ),
                    Fileobj=wbuf,
                    ExtraArgs={
                        "ContentType": f"image/{format.lower()}",
                        "Metadata": metadata,
                    },
                )


class SnsImageConvertProcessor(ImageConvertProcessor):
    @tracer.capture_method
    def process_records(
        self,
        records: typing.List[typing.Dict[str, typing.Any]],
    ) -> None:
        for record in records:
            s3_event = json.loads(record["Sns"]["Message"])
            self._process_s3_records(s3_event["Records"])


class SqsImageConvertProcessor(ImageConvertProcessor):
    @tracer.capture_method
    def _record_handler(self, record: SQSRecord):
        logger.debug(record.body)
        s3_event = json.loads(record.body)
        self._process_s3_records(s3_event["Records"])

    @tracer.capture_method
    def process_records(
        self,
        records: typing.List[typing.Dict[str, typing.Any]],
    ) -> None:
        with processor(records=records, handler=self._record_handler):
            processed_messages: typing.List[
                typing.Union[SuccessResponse, FailureResponse]
            ] = processor.process()
            logger.debug(processed_messages)


@logger.inject_lambda_context
@tracer.capture_lambda_handler
def lambda_handler(event, context: LambdaContext) -> None:
    logger.debug(event)

    try:
        format = Format(os.getenv("APP_FORMAT"))
    except ValueError:
        format = None
    try:
        resize = int(os.getenv("APP_RESIZE"))
    except (ValueError, TypeError):
        resize = None
    config = ConvertConfig(
        bucket_name=os.getenv("BUCKET_NAME"),
        format=format,
        resize=resize,
    )

    use_sqs = strtobool(os.getenv("APP_USE_SQS", "False"))
    processor = (
        SqsImageConvertProcessor if use_sqs else SnsImageConvertProcessor
    )(config)
    processor.process_records(event["Records"])
