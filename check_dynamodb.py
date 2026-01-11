#!/usr/bin/env python3
"""
Vérifier le contenu de DynamoDB
"""

import boto3
import json
from config.config import Config

# Créer un client DynamoDB
dynamodb = boto3.client('dynamodb', region_name=Config.AWS_REGION)

print("Vérification de la table DynamoDB...")
print(f"Région: {Config.AWS_REGION}")
print(f"Table: {Config.DYNAMODB_TABLE_NAME}")

try:
    # Scanner la table
    response = dynamodb.scan(TableName=Config.DYNAMODB_TABLE_NAME)
    items = response.get('Items', [])
    
    print(f"\nNombre d'éléments dans la table: {len(items)}")
    
    if items:
        print("\nDernier élément ajouté:")
        
        # Convertir manuellement depuis le format DynamoDB
        last_item = {}
        for key, value_dict in items[-1].items():
            if 'S' in value_dict:
                last_item[key] = value_dict['S']
            elif 'N' in value_dict:
                num_str = value_dict['N']
                try:
                    if '.' in num_str:
                        last_item[key] = float(num_str)
                    else:
                        last_item[key] = int(num_str)
                except ValueError:
                    last_item[key] = num_str
            elif 'BOOL' in value_dict:
                last_item[key] = value_dict['BOOL']
        
        # Afficher en JSON
        print(json.dumps(last_item, indent=2, ensure_ascii=False))
        
        # Vérifier les données extraites
        if 'raw_data' in last_item:
            try:
                raw_data = json.loads(last_item['raw_data'])
                print("\nDonnées extraites (raw_data):")
                print(json.dumps(raw_data, indent=2, ensure_ascii=False))
            except:
                print("\nImpossible de parser raw_data")
    
    else:
        print("\nLa table est vide")
        
except Exception as e:
    print(f"\nErreur: {e}")
    import traceback
    traceback.print_exc()
