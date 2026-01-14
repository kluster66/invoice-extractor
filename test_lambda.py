#!/usr/bin/env python3
"""
Script pour tester la fonction Lambda.
"""

import subprocess
import json
import base64

def test_lambda():
    """Teste la fonction Lambda."""
    print("Test de la fonction Lambda...")
    
    # Créer un payload de test (simulant un événement S3)
    payload = {
        "Records": [
            {
                "eventVersion": "2.1",
                "eventSource": "aws:s3",
                "awsRegion": "us-west-2",
                "eventTime": "2026-01-13T20:30:00.000Z",
                "eventName": "ObjectCreated:Put",
                "s3": {
                    "s3SchemaVersion": "1.0",
                    "configurationId": "testConfigId",
                    "bucket": {
                        "name": "invoice-extractor-bucket-1768335495",
                        "arn": "arn:aws:s3:::invoice-extractor-bucket-1768335495"
                    },
                    "object": {
                        "key": "test-invoice.pdf",
                        "size": 225441,
                        "eTag": "test-etag",
                        "versionId": "test-version-id"
                    }
                }
            }
        ]
    }
    
    # Convertir en JSON puis en base64
    payload_json = json.dumps(payload)
    payload_b64 = base64.b64encode(payload_json.encode('utf-8')).decode('utf-8')
    
    # Appeler la fonction Lambda
    cmd = f"aws lambda invoke --function-name invoice-extractor-prod --region us-west-2 --payload '{payload_b64}' response.json"
    
    print(f"Exécution: {cmd}")
    
    result = subprocess.run(
        cmd,
        shell=True,
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='ignore'
    )
    
    if result.returncode == 0:
        print("✅ Fonction Lambda exécutée avec succès")
        
        # Lire la réponse
        try:
            with open('response.json', 'r') as f:
                response = json.load(f)
            print(f"Réponse: {json.dumps(response, indent=2)}")
        except:
            print("Réponse (raw):")
            with open('response.json', 'r') as f:
                print(f.read())
    else:
        print("❌ Erreur lors de l'exécution")
        print(f"Stderr: {result.stderr}")
    
    # Vérifier les logs
    print("\n🔍 Vérification des logs...")
    cmd = "aws logs describe-log-streams --log-group-name /aws/lambda/invoice-extractor-prod --region us-west-2 --query 'logStreams[0].logStreamName' --output text"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    
    if result.stdout.strip() and result.stdout.strip() != 'None':
        log_stream = result.stdout.strip()
        print(f"Log stream: {log_stream}")
        
        # Récupérer les logs
        cmd = f"aws logs get-log-events --log-group-name /aws/lambda/invoice-extractor-prod --log-stream-name {log_stream} --region us-west-2 --query 'events[].message' --output text"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.stdout:
            print("Logs récents:")
            print(result.stdout[:1000])
        else:
            print("Aucun log trouvé")
    else:
        print("Aucun log stream trouvé")

if __name__ == "__main__":
    test_lambda()
