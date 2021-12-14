import json
import os

import aws_cdk as cdk
import aws_cdk.assertions as assertions
import pytest
from pytest_snapshot.plugin import Snapshot

from multilens.stacks.multilens_stack import MultilensStack


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
            env=env,
        )
        template_json = assertions.Template.from_stack(stack).to_json()

        snapshot.assert_match(
            json.dumps(template_json, indent=2),
            "multilens_stack.json",
        )
