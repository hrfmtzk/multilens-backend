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


line_bot_api = LineBotApi(os.environ["CHANNEL_ACCESS_TOKEN"])
handler = WebhookHandler(os.environ["CHANNEL_SECRET"])


@app.post("/callback")
@tracer.capture_method
def post_handler():
    signature = app.current_event.get_header_value("X-Line-Signature")
    body = app.current_event.body

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        return Response(
            status_code=400,
            content_type="application/json",
            body=json.dumps({"message": "Invalid signature"}),
        )

    return {"message": "OK"}


@handler.add(MessageEvent, message=TextMessage)
def handle_text_message(event: MessageEvent) -> None:
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=event.message.text),
    )


@handler.add(MessageEvent, message=ImageMessage)
def handle_image_message(event: MessageEvent) -> None:
    logger.debug(event.as_json_dict())
    message_id = event.message.id
    image_id = f"L{message_id}"
    user_id = event.source.user_id
    unix_time = event.timestamp / 1000.0

    object_key = f"original/{user_id}/{image_id}"
    message_content = line_bot_api.get_message_content(message_id)

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


@handler.default()
def handle_default(event) -> None:
    logger.debug(event.as_json_dict())


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
