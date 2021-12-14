#!/usr/bin/env python3
import os

import aws_cdk as cdk
from dotenv import find_dotenv, load_dotenv

from multilens.multilens_stack import MultilensStack

load_dotenv(find_dotenv())


app = cdk.App()
MultilensStack(
    app,
    "MultilensStack",
    env=cdk.Environment(
        account=os.getenv("CDK_DEFAULT_ACCOUNT"),
        region=os.getenv("CDK_DEFAULT_REGION"),
    ),
)

app.synth()
