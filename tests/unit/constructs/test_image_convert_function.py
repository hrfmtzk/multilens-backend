import json
import typing
from hashlib import md5
from io import SEEK_SET, BytesIO

import pytest
from aws_lambda_powertools.utilities.typing import LambdaContext
from PIL import Image
from pytest_mock import MockerFixture

from multilens.constructs.image_convert_function.index import (
    ConvertConfig,
    Format,
    ImageConvertProcessor,
    SnsImageConvertProcessor,
    SqsImageConvertProcessor,
    lambda_handler,
)
from tests.helpers import MotoTestClass


class TestImageConvertProcessor(MotoTestClass):
    @pytest.fixture
    def s3_record(self, s3_client) -> typing.Dict[str, typing.Any]:
        bucket_name = "test-input-bucket"
        object_key = "test/image.jpeg"
        s3_client.create_bucket(Bucket=bucket_name)
        with Image.new(
            mode="RGB", size=(200, 200), color=(0, 0, 0)
        ) as image, BytesIO() as buf:
            image.save(buf, "JPEG")
            buf.seek(SEEK_SET)
            s3_client.upload_fileobj(
                Bucket=bucket_name,
                Key=object_key,
                Fileobj=buf,
                ExtraArgs={
                    "ContentType": "image/jpeg",
                },
            )
        s3_record = {
            "eventVersion": "2.1",
            "eventSource": "aws:s3",
            "awsRegion": "us-east-1",
            "eventTime": "2022-01-01T00:00:00.000Z",
            "eventName": "ObjectCreated:Put",
            "userIdentity": {"principalId": "AWS:XXXXXXXXXXXXXXXXXXXXX"},
            "requestParameters": {"sourceIPAddress": "192.168.1.1"},
            "responseElements": {
                "x-amz-request-id": "XXXXXXXXXXXXXXXX",
                "x-amz-id-2": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx/xxxxxxxxxxxxxxxxxxxxxxxx/xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx/",
            },
            "s3": {
                "s3SchemaVersion": "1.0",
                "configurationId": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
                "bucket": {
                    "name": bucket_name,
                    "ownerIdentity": {"principalId": "XXXXXXXXXXXXXX"},
                    "arn": f"arn:aws:s3:::{bucket_name}",
                },
                "object": {
                    "key": object_key,
                    "size": 200000,
                    "eTag": "54ac6050d0ff433a637073253a71fc11",
                    "sequencer": "0061CA8F155D6048ED",
                },
            },
        }
        return s3_record

    @pytest.fixture
    def output_bucket_name(self, s3_client) -> str:
        bucket_name = "test-output-bucket"
        s3_client.create_bucket(Bucket=bucket_name)
        return bucket_name

    @pytest.fixture
    def target(self) -> typing.Type[ImageConvertProcessor]:
        return ImageConvertProcessor

    def test_process_records(
        self, target: typing.Type[ImageConvertProcessor]
    ) -> None:
        processor = target(ConvertConfig(bucket_name="test"))
        with pytest.raises(NotImplementedError):
            processor.process_records([])

    @pytest.mark.parametrize(
        ("format", "resize"),
        [
            (None, None),
            (Format.WEBP, 400),
        ],
    )
    def test_process_s3_records(
        self,
        s3_record: typing.Dict[str, typing.Any],
        output_bucket_name: str,
        target: typing.Type[ImageConvertProcessor],
        format: typing.Optional[Format],
        resize: typing.Optional[int],
    ) -> None:
        processor = target(
            ConvertConfig(
                bucket_name=output_bucket_name,
                format=format,
                resize=resize,
            )
        )
        processor._process_s3_records([s3_record])


class TestSnsImageConvertProcessor:
    @pytest.fixture
    def target(self) -> SnsImageConvertProcessor:
        return SnsImageConvertProcessor(
            ConvertConfig(bucket_name="test-bucket")
        )

    def test_process_records(
        self,
        target: SnsImageConvertProcessor,
        mocker: MockerFixture,
    ) -> None:
        s3_event = {"Records": []}
        records = [
            {
                "EventSource": "aws:sns",
                "EventVersion": "1.0",
                "EventSubscriptionArn": "arn:aws:sns:us-east-1:123456789012:ExampleTopic",
                "Sns": {
                    "Type": "Notification",
                    "MessageId": "95df01b4-ee98-5cb9-9903-4c221d41eb5e",
                    "TopicArn": "arn:aws:sns:us-east-1:123456789012:ExampleTopic",
                    "Subject": "example subject",
                    "Message": json.dumps(s3_event),
                    "Timestamp": "1970-01-01T00:00:00.000Z",
                    "SignatureVersion": "1",
                    "Signature": "EXAMPLE",
                    "SigningCertUrl": "EXAMPLE",
                    "UnsubscribeUrl": "EXAMPLE",
                    "MessageAttributes": {
                        "Test": {"Type": "String", "Value": "TestString"},
                        "TestBinary": {"Type": "Binary", "Value": "TestBinary"},
                    },
                },
            },
        ]
        target._process_s3_records = mocker.Mock()

        target.process_records(records=records)

        target._process_s3_records.assert_called_once_with([])


class TestSqsImageConvertProcessor:
    @pytest.fixture
    def target(self) -> SqsImageConvertProcessor:
        return SqsImageConvertProcessor(
            ConvertConfig(bucket_name="test-bucket")
        )

    def test_process_records(
        self,
        target: SqsImageConvertProcessor,
        mocker: MockerFixture,
    ) -> None:
        s3_event = {"Records": []}
        body = json.dumps(s3_event)
        records = [
            {
                "messageId": "19dd0b57-b21e-4ac1-bd88-01bbb068cb78",
                "receiptHandle": "MessageReceiptHandle",
                "body": body,
                "attributes": {
                    "ApproximateReceiveCount": "1",
                    "SentTimestamp": "1523232000000",
                    "SenderId": "123456789012",
                    "ApproximateFirstReceiveTimestamp": "1523232000001",
                },
                "messageAttributes": {},
                "md5OfBody": md5(body.encode()).hexdigest(),
                "eventSource": "aws:sqs",
                "eventSourceARN": "arn:aws:sqs:us-east-1:123456789012:MyQueue",
                "awsRegion": "us-east-1",
            },
        ]
        target._process_s3_records = mocker.Mock()

        target.process_records(records=records)

        target._process_s3_records.assert_called_once_with([])


class TestImageConvert(MotoTestClass):
    @pytest.fixture
    def target(
        self,
    ) -> typing.Callable[[typing.Dict[str, typing.Any], LambdaContext], None]:
        return lambda_handler

    def test_lambda_handler(
        self,
        target: typing.Callable[
            [typing.Dict[str, typing.Any], LambdaContext], None
        ],
        lambda_context: LambdaContext,
        mocker: MockerFixture,
    ) -> None:
        lambda_event = {"Records": []}
        mocker.patch(
            "multilens.constructs.image_convert_function.index.SnsImageConvertProcessor"
        )
        target(lambda_event, lambda_context)
