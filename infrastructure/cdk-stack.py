#!/usr/bin/env python3
"""
Stack CDK pour le déploiement de l'extracteur de factures
"""

from aws_cdk import (
    Stack,
    Duration,
    RemovalPolicy,
    aws_s3 as s3,
    aws_lambda as lambda_,
    aws_dynamodb as dynamodb,
    aws_events as events,
    aws_events_targets as targets,
    aws_iam as iam,
    aws_logs as logs,
    CfnOutput
)
from constructs import Construct


class InvoiceExtractorStack(Stack):
    """Stack CDK pour l'extracteur de factures"""

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Configuration
        bucket_name = f"invoice-extractor-bucket-{self.account}"
        table_name = "invoices"
        function_name = "invoice-extractor"
        bedrock_model_id = "anthropic.claude-3-sonnet-20240229-v1:0"

        # 1. Bucket S3 pour les factures
        invoice_bucket = s3.Bucket(
            self, "InvoiceBucket",
            bucket_name=bucket_name,
            removal_policy=RemovalPolicy.RETAIN,
            versioned=True,
            lifecycle_rules=[
                s3.LifecycleRule(
                    id="MoveToGlacier",
                    transitions=[
                        s3.Transition(
                            storage_class=s3.StorageClass.GLACIER,
                            transition_after=Duration.days(90)
                        )
                    ]
                ),
                s3.LifecycleRule(
                    id="ExpireOldObjects",
                    expiration=Duration.days(365)
                )
            ]
        )

        # 2. Table DynamoDB pour les factures extraites
        invoices_table = dynamodb.Table(
            self, "InvoicesTable",
            table_name=table_name,
            partition_key=dynamodb.Attribute(
                name="invoice_id",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PROVISIONED,
            read_capacity=5,
            write_capacity=5,
            removal_policy=RemovalPolicy.RETAIN
        )

        # Ajouter des indexes globaux secondaires
        invoices_table.add_global_secondary_index(
            index_name="numero_facture-index",
            partition_key=dynamodb.Attribute(
                name="numero_facture",
                type=dynamodb.AttributeType.STRING
            ),
            projection_type=dynamodb.ProjectionType.ALL,
            read_capacity=5,
            write_capacity=5
        )

        invoices_table.add_global_secondary_index(
            index_name="date_facture-index",
            partition_key=dynamodb.Attribute(
                name="date_facture",
                type=dynamodb.AttributeType.STRING
            ),
            projection_type=dynamodb.ProjectionType.ALL,
            read_capacity=5,
            write_capacity=5
        )

        invoices_table.add_global_secondary_index(
            index_name="fournisseur-index",
            partition_key=dynamodb.Attribute(
                name="fournisseur",
                type=dynamodb.AttributeType.STRING
            ),
            projection_type=dynamodb.ProjectionType.ALL,
            read_capacity=5,
            write_capacity=5
        )

        # 3. Fonction Lambda
        # Créer le rôle IAM pour Lambda
        lambda_role = iam.Role(
            self, "InvoiceExtractorRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaBasicExecutionRole"
                )
            ]
        )

        # Permissions S3
        invoice_bucket.grant_read(lambda_role)
        
        # Permissions Bedrock
        lambda_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "bedrock:InvokeModel",
                    "bedrock:ListFoundationModels"
                ],
                resources=["*"]
            )
        )
        
        # Permissions DynamoDB
        invoices_table.grant_read_write_data(lambda_role)

        # Créer la fonction Lambda
        invoice_extractor_function = lambda_.Function(
            self, "InvoiceExtractorFunction",
            function_name=function_name,
            runtime=lambda_.Runtime.PYTHON_3_8,
            handler="main.lambda_handler",
            code=lambda_.Code.from_asset("src"),
            role=lambda_role,
            timeout=Duration.seconds(300),
            memory_size=1024,
            environment={
                "AWS_REGION": self.region,
                "DYNAMODB_TABLE_NAME": table_name,
                "S3_INPUT_BUCKET": invoice_bucket.bucket_name,
                "BEDROCK_MODEL_ID": bedrock_model_id,
                "BEDROCK_MAX_TOKENS": "1000",
                "BEDROCK_TEMPERATURE": "0.1",
                "LOG_LEVEL": "INFO"
            },
            log_retention=logs.RetentionDays.ONE_MONTH
        )

        # 4. Configurer le déclencheur S3
        invoice_bucket.add_event_notification(
            s3.EventType.OBJECT_CREATED,
            targets.LambdaFunction(invoice_extractor_function)
        )

        # 5. Dashboard CloudWatch (simplifié)
        # Note: Pour un dashboard complet, utiliser aws_cloudwatch.Dashboard
        
        # 6. Outputs
        CfnOutput(
            self, "InvoiceBucketName",
            value=invoice_bucket.bucket_name,
            description="Nom du bucket S3 pour déposer les factures"
        )
        
        CfnOutput(
            self, "InvoiceExtractorFunctionArn",
            value=invoice_extractor_function.function_arn,
            description="ARN de la fonction Lambda"
        )
        
        CfnOutput(
            self, "InvoicesTableName",
            value=invoices_table.table_name,
            description="Nom de la table DynamoDB"
        )
        
        CfnOutput(
            self, "LambdaConsoleUrl",
            value=f"https://{self.region}.console.aws.amazon.com/lambda/home?region={self.region}#/functions/{function_name}",
            description="URL de la console Lambda"
        )
        
        CfnOutput(
            self, "S3ConsoleUrl",
            value=f"https://s3.console.aws.amazon.com/s3/buckets/{invoice_bucket.bucket_name}",
            description="URL de la console S3"
        )


# App pour le déploiement
if __name__ == "__main__":
    from aws_cdk import App
    
    app = App()
    InvoiceExtractorStack(app, "InvoiceExtractorStack")
    app.synth()
