#!/usr/bin/env python3
"""
Script de nettoyage AWS pour Invoice Extractor.
Supprime toutes les ressources AWS créées par le déploiement.
"""

import subprocess
import sys
import json
import os
import time
import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

load_dotenv()

REGION     = os.getenv("AWS_REGION", "us-west-2")
STACK_NAME = "invoice-extractor"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def run_command(command):
    """Exécute une commande shell et retourne (success, stdout, stderr)."""
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        return result.returncode == 0, result.stdout.strip(), result.stderr.strip()
    except Exception as e:
        return False, "", str(e)


def warn(msg):
    print(f"   ⚠️  {msg}")


def ok(msg):
    print(f"   ✅ {msg}")


def err(msg):
    print(f"   ❌ {msg}")


# ---------------------------------------------------------------------------
# S3 — vidage complet incluant toutes les versions
# ---------------------------------------------------------------------------

def empty_bucket(bucket_name: str) -> bool:
    """
    Vide un bucket S3 (sans versioning).
    Retourne True si le bucket est vide (ou n'existe pas), False en cas d'erreur.
    """
    s3 = boto3.client("s3", region_name=REGION)

    # Vérifier que le bucket existe
    try:
        s3.head_bucket(Bucket=bucket_name)
    except ClientError as e:
        code = e.response["Error"]["Code"]
        if code in ("404", "NoSuchBucket"):
            ok(f"Bucket déjà inexistant : {bucket_name}")
            return True
        warn(f"Impossible d'accéder au bucket {bucket_name} : {e}")
        return False

    print(f"   Vidage du bucket : {bucket_name}")
    try:
        paginator = s3.get_paginator("list_objects_v2")
        total = 0
        for page in paginator.paginate(Bucket=bucket_name):
            objects = page.get("Contents", [])
            if objects:
                s3.delete_objects(
                    Bucket=bucket_name,
                    Delete={"Objects": [{"Key": o["Key"]} for o in objects], "Quiet": True},
                )
                total += len(objects)
        ok(f"Bucket vidé ({total} objet(s))")
        return True
    except ClientError as e:
        err(f"Erreur lors du vidage de {bucket_name} : {e}")
        return False


def get_bucket_name_from_stack() -> str | None:
    """Récupère le nom du bucket depuis les outputs CloudFormation."""
    cf = boto3.client("cloudformation", region_name=REGION)
    try:
        resp = cf.describe_stacks(StackName=STACK_NAME)
        outputs = resp["Stacks"][0].get("Outputs", [])
        for o in outputs:
            if o["OutputKey"] == "BucketName":
                return o["OutputValue"]
    except ClientError:
        pass
    # Fallback : lire depuis .env
    return os.getenv("S3_INPUT_BUCKET")


# ---------------------------------------------------------------------------
# CloudFormation
# ---------------------------------------------------------------------------

def cleanup_cloudformation() -> bool:
    print(f"\n1. Nettoyage de la stack CloudFormation ({STACK_NAME})...")

    cf = boto3.client("cloudformation", region_name=REGION)

    # Vérifier si la stack existe
    try:
        resp = cf.describe_stacks(StackName=STACK_NAME)
        stack = resp["Stacks"][0]
        status = stack["StackStatus"]
    except ClientError as e:
        if "does not exist" in str(e):
            ok("Stack inexistante — rien à faire")
            return True
        err(f"Impossible de décrire la stack : {e}")
        return False

    print(f"   Statut actuel : {status}")

    # États terminaux non-supprimables — informer et continuer
    if status == "DELETE_COMPLETE":
        ok("Stack déjà supprimée")
        return True

    if status not in (
        "CREATE_COMPLETE", "UPDATE_COMPLETE", "ROLLBACK_COMPLETE",
        "UPDATE_ROLLBACK_COMPLETE", "DELETE_FAILED",
    ):
        err(f"État inattendu '{status}' — suppression risquée. Vérifiez la console AWS.")
        return False

    # Vider le bucket S3 AVANT de lancer la suppression de stack
    bucket = get_bucket_name_from_stack()
    if bucket:
        if not empty_bucket(bucket):
            err("Impossible de vider le bucket. Arrêt pour éviter un DELETE_FAILED.")
            return False
    else:
        warn("Nom du bucket introuvable — la suppression de stack pourrait échouer.")

    # Lancer la suppression
    print("   Suppression de la stack en cours...")
    try:
        cf.delete_stack(StackName=STACK_NAME)
    except ClientError as e:
        err(f"Impossible de lancer la suppression : {e}")
        return False

    # Attendre avec feedback
    print("   Attente (peut prendre 2-5 minutes)...", end="", flush=True)
    waiter = cf.get_waiter("stack_delete_complete")
    try:
        waiter.wait(
            StackName=STACK_NAME,
            WaiterConfig={"Delay": 10, "MaxAttempts": 60},
        )
        print(" OK")
        ok("Stack supprimée")
        return True
    except Exception:
        print()
        # Diagnostiquer ce qui a bloqué
        try:
            resp = cf.describe_stacks(StackName=STACK_NAME)
            final_status = resp["Stacks"][0]["StackStatus"]
        except ClientError:
            final_status = "UNKNOWN"

        if final_status == "DELETE_FAILED":
            # Lister les ressources bloquantes
            try:
                events = cf.describe_stack_events(StackName=STACK_NAME)["StackEvents"]
                failed = [
                    e for e in events
                    if e.get("ResourceStatus") == "DELETE_FAILED"
                ]
                if failed:
                    err("Ressources bloquant la suppression :")
                    for f in failed[:5]:
                        print(f"     • {f['LogicalResourceId']} : {f.get('ResourceStatusReason', '?')}")
            except ClientError:
                pass

        err(f"Suppression échouée (statut final : {final_status})")
        err("Astuce : relancez cleanup.py — le bucket est maintenant vide.")
        return False


# ---------------------------------------------------------------------------
# S3 — nettoyage des buckets résiduels
# ---------------------------------------------------------------------------

def cleanup_s3_buckets() -> bool:
    print("\n2. Vérification des buckets S3 résiduels...")

    s3 = boto3.client("s3", region_name=REGION)
    try:
        buckets = s3.list_buckets()["Buckets"]
    except ClientError as e:
        warn(f"Impossible de lister les buckets : {e}")
        return True

    targets = [
        b["Name"] for b in buckets
        if "invoice-input" in b["Name"] or "invoice-extractor" in b["Name"]
    ]

    if not targets:
        ok("Aucun bucket résiduel")
        return True

    all_ok = True
    for bucket in targets:
        print(f"   Suppression bucket résiduel : {bucket}")
        if not empty_bucket(bucket):
            all_ok = False
            continue
        try:
            s3.delete_bucket(Bucket=bucket)
            ok(f"Bucket supprimé : {bucket}")
        except ClientError as e:
            err(f"Impossible de supprimer {bucket} : {e}")
            all_ok = False

    return all_ok


# ---------------------------------------------------------------------------
# DynamoDB
# ---------------------------------------------------------------------------

def cleanup_dynamodb_tables() -> bool:
    print("\n3. Nettoyage des tables DynamoDB...")

    ddb = boto3.client("dynamodb", region_name=REGION)
    try:
        tables = ddb.list_tables()["TableNames"]
    except ClientError as e:
        warn(f"Impossible de lister les tables : {e}")
        return True

    targets = [t for t in tables if "invoice" in t.lower()]

    if not targets:
        ok("Aucune table résiduelle")
        return True

    all_ok = True
    for table in targets:
        try:
            ddb.delete_table(TableName=table)
            ok(f"Table supprimée : {table}")
        except ClientError as e:
            err(f"Impossible de supprimer {table} : {e}")
            all_ok = False

    return all_ok


# ---------------------------------------------------------------------------
# Lambda
# ---------------------------------------------------------------------------

def cleanup_lambda_functions() -> bool:
    print("\n4. Nettoyage des fonctions Lambda...")

    lmb = boto3.client("lambda", region_name=REGION)
    try:
        functions = lmb.list_functions()["Functions"]
    except ClientError as e:
        warn(f"Impossible de lister les fonctions : {e}")
        return True

    targets = [
        f["FunctionName"] for f in functions
        if "invoice-extractor" in f["FunctionName"]
    ]

    if not targets:
        ok("Aucune fonction résiduelle")
        return True

    all_ok = True
    for fn in targets:
        try:
            lmb.delete_function(FunctionName=fn)
            ok(f"Fonction supprimée : {fn}")
        except ClientError as e:
            err(f"Impossible de supprimer {fn} : {e}")
            all_ok = False

    return all_ok


# ---------------------------------------------------------------------------
# CloudWatch Logs
# ---------------------------------------------------------------------------

def cleanup_cloudwatch_logs() -> bool:
    print("\n5. Nettoyage des groupes de logs CloudWatch...")

    logs = boto3.client("logs", region_name=REGION)
    try:
        paginator = logs.get_paginator("describe_log_groups")
        log_groups = []
        for page in paginator.paginate():
            log_groups.extend(page["logGroups"])
    except ClientError as e:
        warn(f"Impossible de lister les groupes de logs : {e}")
        return True

    targets = [
        g["logGroupName"] for g in log_groups
        if "invoice-extractor" in g["logGroupName"]
    ]

    if not targets:
        ok("Aucun groupe de logs résiduel")
        return True

    all_ok = True
    for lg in targets:
        try:
            logs.delete_log_group(logGroupName=lg)
            ok(f"Groupe de logs supprimé : {lg}")
        except ClientError as e:
            err(f"Impossible de supprimer {lg} : {e}")
            all_ok = False

    return all_ok


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("NETTOYAGE AWS — INVOICE EXTRACTOR")
    print(f"Région : {REGION}  |  Stack : {STACK_NAME}")
    print("=" * 60)

    # Vérifier les credentials AWS
    success, identity, error = run_command("aws sts get-caller-identity --output text --query Account")
    if not success:
        err("AWS CLI non configuré ou credentials invalides")
        print("Conseil : exécutez 'aws configure'")
        return 1
    print(f"\n✅ Compte AWS : {identity}")

    all_success = True
    all_success &= cleanup_cloudformation()
    all_success &= cleanup_s3_buckets()
    all_success &= cleanup_dynamodb_tables()
    all_success &= cleanup_lambda_functions()
    all_success &= cleanup_cloudwatch_logs()

    print("\n" + "=" * 60)
    if all_success:
        print("✅ NETTOYAGE TERMINÉ AVEC SUCCÈS")
        print("\nVous pouvez redéployer avec : python deploy.py")
    else:
        print("⚠️  NETTOYAGE PARTIEL — certaines ressources n'ont pas pu être supprimées.")
        print("Vérifiez les erreurs ci-dessus et la console AWS.")
        print("Vous pouvez relancer cleanup.py pour retenter.")
    print("=" * 60)

    return 0 if all_success else 1


if __name__ == "__main__":
    sys.exit(main())
