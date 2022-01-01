import json
import os

import aws_cdk as cdk
import aws_cdk.assertions as assertions
import pytest
from aws_cdk import (
    aws_s3 as s3,
)
from pytest_snapshot.plugin import Snapshot

from multilens.constructs.image_convert import ImageConvert
from tests.helpers import ignore_template_assets


class TestImageConvert:
    @pytest.fixture
    def environ(self) -> None:
        return

    @pytest.fixture()
    def app(self, environ) -> cdk.App:
        return cdk.App()

    @pytest.fixture
    def env(self, environ) -> cdk.Environment:
        return cdk.Environment(
            account=os.getenv("CDK_DEFAULT_ACCOUNT"),
            region=os.getenv("CDK_DEFAULT_REGION"),
        )

    def test_full_resource_snapshot(
        self, snapshot: Snapshot, app: cdk.App, env: cdk.Environment
    ) -> None:
        stack = cdk.Stack(app, "Test", env=env)
        ImageConvert(
            stack,
            "ImageConvert",
            use_sqs=True,
            input_bucket_props=s3.BucketProps(),
            output_bucket_props=s3.BucketProps(),
            lambda_log_level="DEBUG",
            lambda_sentry_dsn="https://sentry.example.com",
        )
        template_json = ignore_template_assets(
            assertions.Template.from_stack(stack).to_json()
        )

        snapshot.assert_match(
            json.dumps(template_json, indent=2),
            "convert_image_full_resource.json",
        )

    def test_minimal_resource_snapshot(
        self, snapshot: Snapshot, app: cdk.App, env: cdk.Environment
    ) -> None:
        stack = cdk.Stack(app, "Test", env=env)
        input_bucket = s3.Bucket(stack, "InputBucket")
        output_bucket = s3.Bucket(stack, "OutputBucket")
        ImageConvert(
            stack,
            "ImageConvert",
            use_sqs=False,
            input_bucket=input_bucket,
            output_bucket=output_bucket,
        )
        template_json = ignore_template_assets(
            assertions.Template.from_stack(stack).to_json()
        )

        snapshot.assert_match(
            json.dumps(template_json, indent=2),
            "convert_image_minimal_resource.json",
        )
