import typing
from dataclasses import dataclass
from pathlib import Path

import aws_cdk as cdk
from aws_cdk import (
    aws_s3 as s3,
    aws_s3_notifications as notifications,
    aws_sns_subscriptions as subscriptions,
    aws_lambda as lambda_,
    aws_lambda_event_sources as event_source,
    aws_lambda_python_alpha as lambda_python,
    aws_logs as logs,
    aws_sns as sns,
    aws_sqs as sqs,
)
from constructs import Construct


here = Path(__file__).absolute().parent


@dataclass
class ConvertProps:
    format: str
    resize: str

    def camel_name(self) -> str:
        return f"{self.format.capitalize()}{self.resize.capitalize()}"

    def snake_name(self) -> str:
        return f"{self.format}_{self.resize}"


class ImageConvert(Construct):
    def __init__(
        self,
        scope: Construct,
        id: str,
        use_sqs: bool = False,
        input_bucket: typing.Optional[s3.Bucket] = None,
        input_bukect_props: typing.Optional[s3.BucketProps] = None,
        output_bucket: typing.Optional[s3.Bucket] = None,
        output_bukect_props: typing.Optional[s3.BucketProps] = None,
        lambda_tracing: bool = False,
        lambda_log_level: typing.Optional[str] = None,
        lambda_sentry_dsn: typing.Optional[str] = None,
    ) -> None:
        super().__init__(scope, id)

        self.input_bucket = input_bucket or s3.Bucket(
            self,
            "InputBucket",
            **input_bukect_props._values,
        )
        self.output_bucket = output_bucket or s3.Bucket(
            self,
            "OutputBucket",
            **output_bukect_props._values,
        )

        self.topic = sns.Topic(
            self,
            "Topic",
        )

        self.input_bucket.add_object_created_notification(
            dest=notifications.SnsDestination(self.topic),
        )

        convert_props = [
            ConvertProps(format="original", resize="original"),
            ConvertProps(format="jpeg", resize="400"),
            ConvertProps(format="webp", resize="original"),
            ConvertProps(format="webp", resize="400"),
        ]

        for props in convert_props:
            function = self._add_convert_function(
                convert_props=props,
                use_sqs=use_sqs,
                input_bucket=self.input_bucket,
                output_bucket=self.output_bucket,
                tracing=lambda_tracing,
                log_level=lambda_log_level,
                sentry_dsn=lambda_sentry_dsn,
            )
            if use_sqs:
                self._connect_with_sqs(self.topic, function, props.camel_name())
            else:
                self._connect_direct(self.topic, function)

    def _add_convert_function(
        self,
        convert_props: ConvertProps,
        use_sqs: bool,
        input_bucket: s3.Bucket,
        output_bucket: s3.Bucket,
        tracing: bool = False,
        log_level: typing.Optional[str] = None,
        sentry_dsn: typing.Optional[str] = None,
    ) -> lambda_.Function:
        construct_id = f"Function{convert_props.camel_name()}"
        directory_name = f"image_convert_function"
        log_level = log_level or "INFO"
        sentry_dsn = sentry_dsn or ""
        function = lambda_python.PythonFunction(
            self,
            construct_id,
            entry=str(here / directory_name),
            index="index.py",
            handler="lambda_handler",
            runtime=lambda_.Runtime.PYTHON_3_9,
            environment={
                "APP_FORMAT": convert_props.format,
                "APP_RESIZE": convert_props.resize,
                "APP_USE_SQS": str(use_sqs),
                "LOG_LEVEL": log_level,
                "POWERTOOLS_SERVICE_NAME": "ImageConvert",
                "BUCKET_NAME": output_bucket.bucket_name,
                "SENTRY_DSN": sentry_dsn,
            },
            memory_size=512,
            timeout=cdk.Duration.seconds(15),
            log_retention=logs.RetentionDays.ONE_MONTH,
            tracing=(
                lambda_.Tracing.ACTIVE if tracing else lambda_.Tracing.DISABLED
            ),
        )
        input_bucket.grant_read(function)
        output_bucket.grant_read_write(function)

        return function

    def _connect_direct(
        self, topic: sns.Topic, function: lambda_.Function
    ) -> None:
        function.add_event_source(event_source.SnsEventSource(topic))

    def _connect_with_sqs(
        self,
        topic: sns.Topic,
        function: lambda_.Function,
        queue_id: str,
    ) -> None:
        queue = sqs.Queue(
            self,
            queue_id,
        )
        topic.add_subscription(
            subscriptions.SqsSubscription(
                queue=queue,
                raw_message_delivery=True,
            )
        )
        function.add_event_source(event_source.SqsEventSource(queue))
