#!/usr/bin/env python3
"""
Test de la détection de région AWS
"""

import os
import sys
from pathlib import Path

# Ajouter les répertoires au path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))
sys.path.insert(0, str(current_dir / "src"))

from config.config import Config, get_aws_region


def test_region_detection():
    """Test la détection de région"""
    print("Test de détection de région AWS")
    print("=" * 50)
    
    # Test 1: Sans variable d'environnement
    if 'AWS_REGION' in os.environ:
        original_region = os.environ['AWS_REGION']
        del os.environ['AWS_REGION']
    
    print("\n1. Sans variable AWS_REGION (utilise AWS CLI):")
    region = get_aws_region()
    print(f"   Région détectée: {region}")
    
    # Test 2: Avec variable d'environnement
    print("\n2. Avec variable AWS_REGION=eu-west-1:")
    os.environ['AWS_REGION'] = 'eu-west-1'
    region = get_aws_region()
    print(f"   Région détectée: {region}")
    
    # Test 3: Configuration complète
    print("\n3. Configuration complète:")
    Config.print_config()
    
    # Test 4: Clients AWS
    print("\n4. Test des clients AWS:")
    try:
        from src.bedrock_client import BedrockClient
        from src.dynamodb_client import DynamoDBClient
        
        bedrock = BedrockClient()
        dynamodb = DynamoDBClient()
        
        print(f"   BedrockClient région: {bedrock.region}")
        print(f"   DynamoDBClient région: {dynamodb.region}")
        print(f"   DynamoDBClient table: {dynamodb.table_name}")
        
    except Exception as e:
        print(f"   Erreur: {e}")
    
    # Nettoyer
    if 'AWS_REGION' in os.environ:
        del os.environ['AWS_REGION']
    if 'original_region' in locals():
        os.environ['AWS_REGION'] = original_region
    
    print("\n" + "=" * 50)
    print("✅ Test terminé")


if __name__ == "__main__":
    test_region_detection()
