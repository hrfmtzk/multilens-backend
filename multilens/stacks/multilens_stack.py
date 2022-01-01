from aws_cdk import (
    aws_s3 as s3,
    Stack,
)
from constructs import Construct

from multilens.constructs.image_convert import ImageConvert


class MultilensStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        image_convert = ImageConvert(
            self,
            "ImageConvert",
            use_sqs=False,
            input_bukect_props=s3.BucketProps(),
            output_bukect_props=s3.BucketProps(),
            lambda_log_level="DEBUG",
        )
