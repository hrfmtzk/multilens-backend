import json
import os
import typing
from distutils.util import strtobool

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
from sentry_sdk import capture_exception
from sentry_sdk.integrations.aws_lambda import AwsLambdaIntegration


FORMAT = os.getenv("APP_FORMAT")
RESIZE = os.getenv("APP_RESIZE")
USE_SQS = strtobool(os.getenv("APP_USE_SQS"))
SENTRY_DSN = os.environ.get("SENTRY_DSN")


logger = Logger()
tracer = Tracer()


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


@tracer.capture_method
def sqs_record_handler(record: SQSRecord):
    logger.debug(record.body)
    event = json.loads(record.body)
    process_s3_created_event(event)


@tracer.capture_method
def process_s3_created_event(event: typing.Dict[str, typing.Any]) -> None:
    logger.debug(event)


@logger.inject_lambda_context
@tracer.capture_lambda_handler
def lambda_handler(event, context: LambdaContext):
    logger.debug(event)

    if USE_SQS:
        records = event["Records"]
        with processor(records=records, handler=sqs_record_handler):
            processed_messages: typing.List[
                typing.Union[SuccessResponse, FailureResponse]
            ] = processor.process()
            logger.debug(processed_messages)
        return processor.response()
    else:
        s3_event = json.dumps(event["Records"][0]["Sns"]["Message"])
        process_s3_created_event(s3_event)
