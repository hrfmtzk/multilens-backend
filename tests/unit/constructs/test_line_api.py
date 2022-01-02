import json
import os

import aws_cdk as cdk
import aws_cdk.assertions as assertions
import pytest
from aws_cdk import (
    aws_s3 as s3,
)
from pytest_snapshot.plugin import Snapshot

from multilens.constructs.line_api import LineApi, LineApiCredential
from tests.helpers import ignore_template_assets


class TestLineApi:
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
        LineApi(
            stack,
            "LineApi",
            line_credential=LineApiCredential(
                access_token="access_token",
                secret="secret",
            ),
            bucket_props=s3.BucketProps(),
            lambda_log_level="DEBUG",
            lambda_sentry_dsn="https://sentry.example.com",
        )
        template_json = ignore_template_assets(
            assertions.Template.from_stack(stack).to_json()
        )

        snapshot.assert_match(
            json.dumps(template_json, indent=2),
            "line_api_full_resource.json",
        )

    def test_minimal_resource_snapshot(
        self, snapshot: Snapshot, app: cdk.App, env: cdk.Environment
    ) -> None:
        stack = cdk.Stack(app, "Test", env=env)
        bucket = s3.Bucket(stack, "Bucket")
        LineApi(
            stack,
            "LineApi",
            line_credential=LineApiCredential(
                access_token="access_token",
                secret="secret",
            ),
            bucket=bucket,
            lambda_log_level="DEBUG",
            lambda_sentry_dsn="https://sentry.example.com",
        )
        template_json = ignore_template_assets(
            assertions.Template.from_stack(stack).to_json()
        )

        snapshot.assert_match(
            json.dumps(template_json, indent=2),
            "line_api_minimal_resource.json",
        )
