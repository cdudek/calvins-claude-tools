---
name: aws-manage
description: Runs the AWS CLI with your credentials (env, AWS_PROFILE or SSO, ~/.aws, or keys in ~/.zshrc) without ever reading or printing them. Use when the user mentions AWS, S3, EC2, Lambda, IAM, CloudFront, Route 53, RDS, DynamoDB, SES, SQS, SNS, CloudWatch, Bedrock, an AWS bill or cost, or asks to list, inspect, upload, download, create or change anything in AWS. Skip for Google Cloud, Cloudflare (cloudflare-manage) and Vercel.
allowed-tools: "Bash(bash */aws-manage/scripts/*)"
user_invocable: true
metadata:
  version: 1.0.0
  author: calvindudek
---

# AWS

Every AWS call goes through the wrapper in this skill's folder, never bare `aws`:

```bash
bash <skill>/scripts/aws <aws cli args>
```

It uses the standard credential chain (env vars, `AWS_PROFILE`, SSO, `~/.aws`); when none is set it reads `AWS_ACCESS_KEY` and `AWS_SECRET_ACCESS_KEY` from the user's zsh profile. The region defaults to `eu-central-1` (Frankfurt); override per call with `--region`.

## Prerequisites

| Needs | How |
| --- | --- |
| AWS CLI v2 | `brew install awscli` |
| Credentials | `aws sso login --profile NAME` and `AWS_PROFILE=NAME`, or access keys exported in the shell profile. Never pasted into the chat. |

## Start of every session

```bash
bash <skill>/scripts/aws sts get-caller-identity
```

Shows the account and the identity, which tells you what the credentials may touch.

## Rules

- **Never print or read the keys:** no `cat` of `~/.zshrc` or `~/.aws/credentials`, no `env`, `printenv`, `echo $AWS_*`, `aws configure`, `aws configure export-credentials` or `set -x` around the wrapper.
- **Read freely:** `list-*`, `describe-*`, `get-*`, `s3 ls`, `ce get-cost-and-usage`, `logs tail`.
- **Ask before any write:** create, put, update, delete, `s3 cp`/`sync`/`rm` to a bucket, IAM changes, DNS changes, anything that costs money or becomes public. State the exact command and its effect, then wait for a yes.
- **Never** `s3 rm --recursive`, `s3 sync --delete`, `delete-bucket`, `terminate-instances`, a Route 53 record deletion or IAM key creation unless the user named that exact resource in the same turn.
- Keep output small: `--output json` with `--query` (JMESPath); `--output table` only for a list the user reads.

## Common calls

```bash
bash <skill>/scripts/aws s3 ls s3://BUCKET/PREFIX/ --recursive --human-readable --summarize
bash <skill>/scripts/aws lambda list-functions --query 'Functions[].[FunctionName,Runtime,LastModified]' --output table
bash <skill>/scripts/aws logs tail /aws/lambda/FUNCTION --since 1h
bash <skill>/scripts/aws route53 list-resource-record-sets --hosted-zone-id ZONE --query "ResourceRecordSets[?Type=='MX']"
bash <skill>/scripts/aws sesv2 get-email-identity --email-identity example.com
bash <skill>/scripts/aws ce get-cost-and-usage --time-period Start=YYYY-MM-01,End=YYYY-MM-DD --granularity MONTHLY --metrics UnblendedCost --group-by Type=DIMENSION,Key=SERVICE
```

Before a Route 53 change, save the record set you will change; a change batch is built from the exact current values (an UPSERT or DELETE with a stale value fails or overwrites).

## In scripts

A script calls the wrapper (`subprocess`, `execFile`) so the credentials stay inside it. Never copy keys into a `.env` or into code.
