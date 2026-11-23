#!/usr/bin/env python3

import json
import sys

import boto3
from botocore.exceptions import ClientError

REGION = "us-east-1"
STACK_NAME = "bug-report-tool-stack"
GATEWAY_ID = "bug-report-tool-stack-gateway-ttjlheyatu"
TARGET_NAME = "bugreports"
CONFIG_PATH = "agentcore_config.json"

TOOL_SCHEMA = {
    "name": "create_bug_report",
    "description": (
        "File a bug ticket in the engineering team's tracker. "
        "Call this only after the customer has provided a bug description, "
        "the steps to reproduce it, and their environment. "
        "Returns the new ticket's ID."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "description": {
                "type": "string",
                "description": "What is broken, in the customer's words.",
            },
            "stepsToReproduce": {
                "type": "string",
                "description": "Steps to follow to reproduce the issue.",
            },
            "environment": {
                "type": "string",
                "description": "Customer's environment: browser, OS, device.",
            },
        },
        "required": [
            "description",
            "stepsToReproduce",
            "environment",
        ],
    },
}


def main():
    try:
        cfn = boto3.client("cloudformation", region_name=REGION)
        stacks = cfn.describe_stacks(StackName=STACK_NAME)["Stacks"]
        outputs = {
            item["OutputKey"]: item["OutputValue"]
            for item in stacks[0].get("Outputs", [])
        }

        lambda_arn = outputs["LambdaFunctionArn"]
        gateway_role_arn = outputs["GatewayRoleArn"]
        harness_role_arn = outputs["HarnessExecutionRoleArn"]
        table_name = outputs["BugReportsTableName"]

        control = boto3.client(
            "bedrock-agentcore-control",
            region_name=REGION,
        )

        gateway = control.get_gateway(
            gatewayIdentifier=GATEWAY_ID
        )

        status = gateway.get("status")
        print(f"Existing Gateway: {GATEWAY_ID}")
        print(f"Gateway status: {status}")

        if status != "READY":
            raise RuntimeError(
                f"Gateway is not READY; current status is {status}"
            )

        print(f"Registering Lambda target: {TARGET_NAME}")

        target = control.create_gateway_target(
            gatewayIdentifier=GATEWAY_ID,
            name=TARGET_NAME,
            targetConfiguration={
                "mcp": {
                    "lambda": {
                        "lambdaArn": lambda_arn,
                        "toolSchema": {
                            "inlinePayload": [TOOL_SCHEMA]
                        },
                    }
                }
            },
            credentialProviderConfigurations=[
                {
                    "credentialProviderType": "GATEWAY_IAM_ROLE"
                }
            ],
        )

        target_id = target["targetId"]

        config = {
            "region": REGION,
            "stack_name": STACK_NAME,
            "table_name": table_name,
            "lambda_arn": lambda_arn,
            "gateway_name": "bug-report-tool-stack-gateway",
            "gateway_id": GATEWAY_ID,
            "gateway_arn": gateway["gatewayArn"],
            "gateway_target_id": target_id,
            "gateway_target_name": TARGET_NAME,
            "harness_execution_role_arn": harness_role_arn,
        }

        with open(CONFIG_PATH, "w", encoding="utf-8") as file:
            json.dump(config, file, indent=2)
            file.write("\n")

        print("\nTarget registration request succeeded.")
        print(f"Target ID: {target_id}")
        print(f"Configuration saved to {CONFIG_PATH}")

    except ClientError as exc:
        print("AWS API operation failed:", file=sys.stderr)
        print(exc, file=sys.stderr)
        sys.exit(1)
    except (KeyError, RuntimeError, OSError) as exc:
        print(f"Setup failed: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
