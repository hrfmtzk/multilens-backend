import json
import os
import typing
from io import BytesIO

import boto3
import sentry_sdk
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.event_handler.api_gateway import (
    ApiGatewayResolver,
    Response,
)
from aws_lambda_powertools.logging import correlation_paths
from aws_lambda_powertools.utilities.typing import LambdaContext
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    ImageMessage,
    MessageEvent,
    TextMessage,
    TextSendMessage,
)
from sentry_sdk.integrations.aws_lambda import AwsLambdaIntegration

logger = Logger()
tracer = Tracer()
app = ApiGatewayResolver()


SENTRY_DSN = os.environ.get("SENTRY_DSN")


if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[AwsLambdaIntegration()],
        traces_sample_rate=1.0,
    )


class LineApiHandler:
    def __init__(self, access_token: str, secret: str) -> None:
        self.line_bot_api = LineBotApi(access_token)
        self.handler = WebhookHandler(secret)

        self._register_handlers()

    def _register_handlers(self) -> None:
        self._wrap_register(
            self._handle_text_message,
            MessageEvent,
            TextMessage,
        )
        self._wrap_register(
            self._handle_image_message,
            MessageEvent,
            ImageMessage,
        )
        self.handler._default = self._handle_default

    def _wrap_register(
        self,
        func: typing.Callable[[typing.Any], None],
        event,
        message=None,
    ) -> None:
        def wrap(e: typing.Any) -> None:
            func(e)

        self.handler.add(event, message=message)(wrap)

    def _handle_text_message(self, event: MessageEvent) -> None:
        # Echo
        self.line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=event.message.text),
        )

    def _handle_image_message(self, event: MessageEvent) -> None:
        logger.debug(event.as_json_dict())
        message_id = event.message.id
        image_id = f"L{message_id}"
        user_id = event.source.user_id
        unix_time = event.timestamp / 1000.0

        object_key = f"original/{user_id}/{image_id}"
        message_content = self.line_bot_api.get_message_content(message_id)

        s3 = boto3.client("s3")
        s3.upload_fileobj(
            Fileobj=BytesIO(message_content.content),
            Bucket=os.getenv("BUCKET_NAME"),
            Key=object_key,
            ExtraArgs={
                "ContentType": message_content.content_type,
                "Metadata": {
                    "UserId": user_id,
                    "ImageId": image_id,
                    "Created": str(unix_time),
                },
            },
        )

    def _handle_default(self, event) -> None:
        logger.debug(event.as_json_dict())


@app.post("/callback")
@tracer.capture_method
def post_handler():
    signature = app.current_event.get_header_value("X-Line-Signature")
    body = app.current_event.body

    line_api = LineApiHandler(
        access_token=os.getenv("CHANNEL_ACCESS_TOKEN"),
        secret=os.getenv("CHANNEL_SECRET"),
    )

    try:
        line_api.handler.handle(body, signature)
    except InvalidSignatureError:
        return Response(
            status_code=400,
            content_type="application/json",
            body=json.dumps({"message": "Invalid signature"}),
        )

    return {"message": "OK"}


@logger.inject_lambda_context(
    correlation_id_path=correlation_paths.API_GATEWAY_REST,
)
@tracer.capture_lambda_handler
def lambda_handler(
    event,
    context: LambdaContext,
) -> typing.Dict[str, typing.Any]:
    logger.debug(event)
    return app.resolve(event, context)
