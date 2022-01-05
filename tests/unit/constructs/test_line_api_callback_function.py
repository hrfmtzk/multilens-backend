import json
import os
import typing

import pytest
from aws_lambda_powertools.utilities.typing.lambda_context import LambdaContext
from linebot.exceptions import InvalidSignatureError
from linebot.models.events import MessageEvent
from linebot.models.messages import ImageMessage, TextMessage
from linebot.models.sources import SourceUser
from pytest_mock import MockerFixture

from multilens.constructs.line_api_callback_function.index import (
    LineApiHandler,
    lambda_handler,
)
from tests.helpers import AwsTestClass


class TestLineApiHandler(AwsTestClass):
    @pytest.fixture
    def bucket_name(self, s3_client) -> typing.Generator[str, None, None]:
        bucket_name = "test-bucket"
        s3_client.create_bucket(Bucket=bucket_name)
        os.environ["BUCKET_NAME"] = bucket_name

        yield bucket_name

        del os.environ["BUCKET_NAME"]

    @pytest.fixture
    def target(self, mocker: MockerFixture):
        handler = LineApiHandler(
            access_token="testing",
            secret="testing",
        )
        handler.line_bot_api = mocker.Mock()
        handler.handler = mocker.Mock()
        return handler

    def test_handle_text_message(self, target: LineApiHandler) -> None:
        event = MessageEvent(
            message=TextMessage(text="testing message"),
            reply_token="testing token",
        )

        target._handle_text_message(event)

        target.line_bot_api.reply_message.assert_called_once()

    def test_handle_image_messge(
        self,
        target: LineApiHandler,
        bucket_name: str,
        mocker: MockerFixture,
    ) -> None:
        target.line_bot_api.get_message_content.return_value = mocker.Mock(
            content=b"",
            content_type="image/jpeg",
        )
        event = MessageEvent(
            message=ImageMessage(
                id="id",
            ),
            source=SourceUser(
                user_id="user_id",
            ),
            timestamp=1640962800000,
        )

        target._handle_image_message(event)

    def test_handle_default(self, target: LineApiHandler) -> None:
        event = MessageEvent()

        target._handle_default(event)


class TestLineApi(AwsTestClass):
    @pytest.fixture
    def target(self):
        return lambda_handler

    @pytest.fixture
    def lambda_event(self) -> typing.Dict[str, typing.Any]:
        return {
            "body": "eyJ0ZXN0IjoiYm9keSJ9",
            "resource": "/callback",
            "path": "/callback",
            "httpMethod": "POST",
            "isBase64Encoded": False,
            "queryStringParameters": {},
            "multiValueQueryStringParameters": {},
            "pathParameters": {},
            "stageVariables": {},
            "headers": {
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Encoding": "gzip, deflate, sdch",
                "Accept-Language": "en-US,en;q=0.8",
                "Cache-Control": "max-age=0",
                "CloudFront-Forwarded-Proto": "https",
                "CloudFront-Is-Desktop-Viewer": "true",
                "CloudFront-Is-Mobile-Viewer": "false",
                "CloudFront-Is-SmartTV-Viewer": "false",
                "CloudFront-Is-Tablet-Viewer": "false",
                "CloudFront-Viewer-Country": "US",
                "Host": "1234567890.execute-api.us-east-1.amazonaws.com",
                "Upgrade-Insecure-Requests": "1",
                "User-Agent": "Custom User Agent String",
                "Via": "1.1 08f323deadbeefa7af34d5feb414ce27.cloudfront.net (CloudFront)",
                "X-Amz-Cf-Id": "cDehVQoZnx43VYQb9j2-nvCh-9z396Uhbp027Y2JvkCPNLmGJHqlaA==",
                "X-Forwarded-For": "127.0.0.1, 127.0.0.2",
                "X-Forwarded-Port": "443",
                "X-Forwarded-Proto": "https",
                "X-Line-Signature": "xxxxxxxx",
            },
            "multiValueHeaders": {
                "Accept": [
                    "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
                ],
                "Accept-Encoding": ["gzip, deflate, sdch"],
                "Accept-Language": ["en-US,en;q=0.8"],
                "Cache-Control": ["max-age=0"],
                "CloudFront-Forwarded-Proto": ["https"],
                "CloudFront-Is-Desktop-Viewer": ["true"],
                "CloudFront-Is-Mobile-Viewer": ["false"],
                "CloudFront-Is-SmartTV-Viewer": ["false"],
                "CloudFront-Is-Tablet-Viewer": ["false"],
                "CloudFront-Viewer-Country": ["US"],
                "Host": ["0123456789.execute-api.us-east-1.amazonaws.com"],
                "Upgrade-Insecure-Requests": ["1"],
                "User-Agent": ["Custom User Agent String"],
                "Via": [
                    "1.1 08f323deadbeefa7af34d5feb414ce27.cloudfront.net (CloudFront)"
                ],
                "X-Amz-Cf-Id": [
                    "cDehVQoZnx43VYQb9j2-nvCh-9z396Uhbp027Y2JvkCPNLmGJHqlaA=="
                ],
                "X-Forwarded-For": ["127.0.0.1, 127.0.0.2"],
                "X-Forwarded-Port": ["443"],
                "X-Forwarded-Proto": ["https"],
                "X-Line-Signature": ["xxxxxxxx"],
            },
            "requestContext": {
                "accountId": "123456789012",
                "resourceId": "123456",
                "stage": "prod",
                "requestId": "c6af9ac6-7b61-11e6-9a41-93e8deadbeef",
                "requestTime": "09/Apr/2015:12:34:56 +0000",
                "requestTimeEpoch": 1428582896000,
                "identity": {
                    "cognitoIdentityPoolId": None,
                    "accountId": None,
                    "cognitoIdentityId": None,
                    "caller": None,
                    "accessKey": None,
                    "sourceIp": "127.0.0.1",
                    "cognitoAuthenticationType": None,
                    "cognitoAuthenticationProvider": None,
                    "userArn": None,
                    "userAgent": "Custom User Agent String",
                    "user": None,
                },
                "path": "/callback",
                "resourcePath": "/callback",
                "httpMethod": "POST",
                "apiId": "1234567890",
                "protocol": "HTTP/1.1",
            },
        }

    def test_lambda_handler(
        self,
        target: typing.Callable[
            [typing.Dict[str, typing.Any], LambdaContext],
            typing.Dict[str, typing.Any],
        ],
        lambda_event: typing.Dict[str, typing.Any],
        lambda_context: LambdaContext,
        mocker: MockerFixture,
    ) -> None:
        mocker.patch(
            "multilens.constructs.line_api_callback_function.index.LineApiHandler"
        )

        response = target(lambda_event, lambda_context)

        self.assert_lambda_response(
            response=response,
            status_code=200,
            content_type="application/json",
            json_body={"message": "OK"},
        )

    def test_lambda_handler_error(
        self,
        target: typing.Callable[
            [typing.Dict[str, typing.Any], LambdaContext],
            typing.Dict[str, typing.Any],
        ],
        lambda_event: typing.Dict[str, typing.Any],
        lambda_context: LambdaContext,
        mocker: MockerFixture,
    ) -> None:
        mocked_instance = mocker.Mock()
        mocked_instance.handler.handle.side_effect = InvalidSignatureError
        mocked_class = mocker.patch(
            "multilens.constructs.line_api_callback_function.index.LineApiHandler"
        )
        mocked_class.return_value = mocked_instance

        response = target(lambda_event, lambda_context)

        self.assert_lambda_response(
            response,
            status_code=400,
            content_type="application/json",
            json_body={"message": "Invalid signature"},
        )
