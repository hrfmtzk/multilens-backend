import json
import os

import aws_cdk as cdk
import aws_cdk.assertions as assertions
import pytest
from pytest_snapshot.plugin import Snapshot

from multilens.constructs.line_api import LineApiCredential
from multilens.stacks.multilens_stack import MultilensStack
from tests.helpers import ignore_template_assets


class TestMultilensStack:
    @pytest.fixture
    def environ(self) -> None:
        return

    @pytest.fixture
    def app(self, environ) -> cdk.App:
        return cdk.App()

    @pytest.fixture
    def env(self, environ) -> cdk.Environment:
        return cdk.Environment(
            account=os.getenv("CDK_DEFAULT_ACCOUNT"),
            region=os.getenv("CDK_DEFAULT_REGION"),
        )

    def test_snapshot(
        self, snapshot: Snapshot, app: cdk.App, env: cdk.Environment
    ) -> None:
        stack = MultilensStack(
            app,
            "Multilens",
            line_credential=LineApiCredential(
                access_token="access_token",
                secret="secret",
            ),
            env=env,
        )
        template_json = ignore_template_assets(
            assertions.Template.from_stack(stack).to_json()
        )

        snapshot.assert_match(
            json.dumps(template_json, indent=2),
            "multilens_stack.json",
        )
