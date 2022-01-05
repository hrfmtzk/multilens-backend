from aws_cdk import Stack, aws_s3 as s3
from constructs import Construct

from multilens.constructs.image_convert import ImageConvert
from multilens.constructs.line_api import LineApi, LineApiCredential


class MultilensStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        line_credential: LineApiCredential,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        LineApi(
            self,
            "LineApi",
            line_credential=line_credential,
            bucket_props=s3.BucketProps(),
            lambda_log_level="DEBUG",
        )

        ImageConvert(
            self,
            "ImageConvert",
            use_sqs=False,
            input_bucket_props=s3.BucketProps(),
            output_bucket_props=s3.BucketProps(),
            lambda_log_level="DEBUG",
        )
