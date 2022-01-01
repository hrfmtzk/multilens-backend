import copy
import os
import typing

import boto3
import pytest
from aws_lambda_powertools.utilities.typing import LambdaContext
from moto import mock_s3


def ignore_template_assets(
    template_json: typing.Dict[str, typing.Any]
) -> typing.Dict[str, typing.Any]:
    template = copy.deepcopy(template_json)
    for resource in template["Resources"].values():
        if "Code" not in resource.get("Properties", {}):
            # not target
            continue
        if "ZipFile" in resource["Properties"]["Code"]:
            # keep code to check
            continue
        resource["Properties"]["Code"] = {}
    return template


class MockLambdaContext(LambdaContext):
    def __init__(self):
        self._function_name = "test-fn"
        self._memory_limit_in_mb = 128
        self._invoked_function_arn = (
            "arn:aws:lambda:us-east-1:12345678:function:test-fn"
        )
        self._aws_request_id = "52fdfc07-2182-154f-163f-5f0f9a621d72"


class MotoTestClass:
    @pytest.fixture
    def aws_credentials(self) -> None:
        os.environ["AWS_ACCESS_KEY_ID"] = "testing"
        os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
        os.environ["AWS_SECURITY_TOKEN"] = "testing"
        os.environ["AWS_SESSION_TOKEN"] = "testing"
        os.environ["AWS_DEFAULT_REGION"] = "us-east-1"

    @pytest.fixture
    def s3_client(self, aws_credentials) -> typing.Any:
        with mock_s3():
            s3 = boto3.client("s3")
            yield s3

    @pytest.fixture
    def lambda_context(self) -> LambdaContext:
        return MockLambdaContext()
