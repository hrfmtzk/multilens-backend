import typing
from dataclasses import dataclass
from pathlib import Path

import aws_cdk as cdk
from aws_cdk import (
    aws_apigateway as apigateway,
    aws_lambda as lambda_,
    aws_lambda_python_alpha as lambda_python,
    aws_logs as logs,
    aws_s3 as s3,
    aws_secretsmanager as sm,
    aws_ssm as ssm,
)
from constructs import Construct

here = Path(__file__).absolute().parent


@dataclass
class LineApiCredential:
    access_token: str
    secret: str


class LineApi(Construct):
    def __init__(
        self,
        scope: Construct,
        id: str,
        line_credential: LineApiCredential,
        bucket: typing.Optional[s3.Bucket] = None,
        bucket_props: typing.Optional[s3.BucketProps] = None,
        lambda_tracing: bool = False,
        lambda_log_level: typing.Optional[str] = None,
        lambda_sentry_dsn: typing.Optional[str] = None,
    ) -> None:
        super().__init__(scope, id)
        lambda_log_level = lambda_log_level or "INFO"
        lambda_sentry_dsn = lambda_sentry_dsn or ""

        if bucket is None and bucket_props is None:
            raise ValueError("requires `bucket` or `bucket_props`")

        self.bucket = bucket or s3.Bucket(
            self,
            "Bucket",
            **bucket_props._values,  # type: ignore
        )

        self.callback_function = lambda_python.PythonFunction(
            self,
            "CallbackFunction",
            entry=str(here / "line_api_callback_function"),
            index="index.py",
            handler="lambda_handler",
            runtime=lambda_.Runtime.PYTHON_3_9,
            environment={
                "CHANNEL_ACCESS_TOKEN": line_credential.access_token,
                "CHANNEL_SECRET": line_credential.secret,
                "LOG_LEVEL": lambda_log_level,
                "POWERTOOLS_SERVICE_NAME": "LineApi",
                "BUCKET_NAME": self.bucket.bucket_name,
                "SENTRY_DSN": lambda_sentry_dsn,
            },
            memory_size=512,
            timeout=cdk.Duration.seconds(15),
            log_retention=logs.RetentionDays.ONE_MONTH,
            tracing=(
                lambda_.Tracing.ACTIVE
                if lambda_tracing
                else lambda_.Tracing.DISABLED
            ),
        )
        self.bucket.grant_read_write(self.callback_function)

        self.access_log = logs.LogGroup(
            self,
            "AccessLog",
            retention=logs.RetentionDays.ONE_MONTH,
        )
        self.api = apigateway.RestApi(
            self,
            "Api",
            rest_api_name="LineApi",
            deploy_options=apigateway.StageOptions(
                access_log_destination=apigateway.LogGroupLogDestination(
                    self.access_log
                ),
                access_log_format=apigateway.AccessLogFormat.json_with_standard_fields(
                    caller=False,
                    http_method=True,
                    ip=True,
                    protocol=True,
                    request_time=True,
                    resource_path=True,
                    response_length=True,
                    status=True,
                    user=False,
                ),
            ),
        )
        self.api.root.add_resource("callback").add_method(
            http_method="POST",
            integration=apigateway.LambdaIntegration(
                handler=self.callback_function,
            ),
        )
