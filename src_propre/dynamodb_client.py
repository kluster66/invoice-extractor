"""
Client pour AWS DynamoDB
"""

import json
import logging
import boto3
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class DynamoDBClient:
    """Client pour interagir avec AWS DynamoDB"""
    
    def __init__(self, region: str = None, table_name: str = None):
        """
        Initialise le client DynamoDB
        
        Args:
            region: Région AWS (si None, utilise la configuration)
            table_name: Nom de la table DynamoDB (si None, utilise la configuration)
        """
        from config import Config
        
        self.region = region or Config.AWS_REGION
        self.table_name = table_name or Config.DYNAMODB_TABLE_NAME
        self.client = boto3.client("dynamodb", region_name=self.region)
        self.resource = boto3.resource("dynamodb", region_name=self.region)
        
        # Vérifier que la table existe
        self._ensure_table_exists()
    
    def _ensure_table_exists(self) -> None:
        """
        Vérifie que la table existe, la crée si nécessaire
        """
        try:
            # Essayer de décrire la table
            self.client.describe_table(TableName=self.table_name)
            logger.info(f"Table DynamoDB '{self.table_name}' existe déjà")
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                logger.info(f"Table '{self.table_name}' non trouvée, création...")
                self._create_table()
            else:
                logger.error(f"Erreur lors de la vérification de la table: {str(e)}")
                raise
    
    def _create_table(self) -> None:
        """
        Crée la table DynamoDB pour les factures
        """
        try:
            table = self.resource.create_table(
                TableName=self.table_name,
                KeySchema=[
                    {
                        'AttributeName': 'invoice_id',
                        'KeyType': 'HASH'  # Partition key
                    }
                ],
                AttributeDefinitions=[
                    {
                        'AttributeName': 'invoice_id',
                        'AttributeType': 'S'
                    },
                    {
                        'AttributeName': 'numero_facture',
                        'AttributeType': 'S'
                    },
                    {
                        'AttributeName': 'date_facture',
                        'AttributeType': 'S'
                    },
                    {
                        'AttributeName': 'fournisseur',
                        'AttributeType': 'S'
                    }
                ],
                GlobalSecondaryIndexes=[
                    {
                        'IndexName': 'numero_facture-index',
                        'KeySchema': [
                            {
                                'AttributeName': 'numero_facture',
                                'KeyType': 'HASH'
                            }
                        ],
                        'Projection': {
                            'ProjectionType': 'ALL'
                        },
                        'ProvisionedThroughput': {
                            'ReadCapacityUnits': 5,
                            'WriteCapacityUnits': 5
                        }
                    },
                    {
                        'IndexName': 'date_facture-index',
                        'KeySchema': [
                            {
                                'AttributeName': 'date_facture',
                                'KeyType': 'HASH'
                            }
                        ],
                        'Projection': {
                            'ProjectionType': 'ALL'
                        },
                        'ProvisionedThroughput': {
                            'ReadCapacityUnits': 5,
                            'WriteCapacityUnits': 5
                        }
                    },
                    {
                        'IndexName': 'fournisseur-index',
                        'KeySchema': [
                            {
                                'AttributeName': 'fournisseur',
                                'KeyType': 'HASH'
                            }
                        ],
                        'Projection': {
                            'ProjectionType': 'ALL'
                        },
                        'ProvisionedThroughput': {
                            'ReadCapacityUnits': 5,
                            'WriteCapacityUnits': 5
                        }
                    }
                ],
                ProvisionedThroughput={
                    'ReadCapacityUnits': 5,
                    'WriteCapacityUnits': 5
                }
            )
            
            # Attendre que la table soit créée
            table.meta.client.get_waiter('table_exists').wait(TableName=self.table_name)
            logger.info(f"Table '{self.table_name}' créée avec succès")
            
        except ClientError as e:
            logger.error(f"Erreur lors de la création de la table: {str(e)}")
            raise
    
    def save_invoice_data(self, invoice_data: Dict[str, Any]) -> str:
        """
        Sauvegarde les données de facture dans DynamoDB
        
        Args:
            invoice_data: Données de la facture
            
        Returns:
            ID de la facture
        """
        try:
            # Générer un ID unique
            invoice_id = str(uuid.uuid4())
            
            # Préparer l'item DynamoDB
            item = {
                'invoice_id': invoice_id,
                'created_at': datetime.utcnow().isoformat(),
                'raw_data': json.dumps(invoice_data, ensure_ascii=False)
            }
            
            # Ajouter les champs extraits pour faciliter les requêtes
            extracted_fields = [
                'fournisseur',
                'montant_ht',
                'numero_facture',
                'date_facture',
                'Le numero Chrono du document',
                'La période de couverture',
                'nom du fichier que tu trouves ici',
                'filename',
                'extraction_date',
                'pdf_path'
            ]
            
            for field in extracted_fields:
                if field in invoice_data and invoice_data[field] is not None:
                    # Convertir les types pour DynamoDB
                    value = invoice_data[field]
                    
                    if isinstance(value, (str, int, float, bool)):
                        item[field] = value
                    else:
                        item[field] = str(value)
            
            # Convertir pour DynamoDB
            dynamo_item = self._convert_to_dynamo_format(item)
            
            # Sauvegarder dans DynamoDB
            self.client.put_item(
                TableName=self.table_name,
                Item=dynamo_item
            )
            
            logger.info(f"Facture sauvegardée avec ID: {invoice_id}")
            return invoice_id
            
        except ClientError as e:
            logger.error(f"Erreur DynamoDB: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Erreur inattendue: {str(e)}")
            raise
    
    def _convert_to_dynamo_format(self, item: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """
        Convertit un dictionnaire Python au format DynamoDB
        
        Args:
            item: Item à convertir
            
        Returns:
            Item au format DynamoDB
        """
        dynamo_item = {}
        
        for key, value in item.items():
            if value is None:
                continue
                
            if isinstance(value, str):
                dynamo_item[key] = {'S': value}
            elif isinstance(value, bool):
                dynamo_item[key] = {'BOOL': value}
            elif isinstance(value, (int, float)):
                dynamo_item[key] = {'N': str(value)}
            elif isinstance(value, dict):
                dynamo_item[key] = {'M': self._convert_to_dynamo_format(value)}
            elif isinstance(value, list):
                # Convertir les listes simples
                if all(isinstance(v, str) for v in value):
                    dynamo_item[key] = {'SS': value}
                elif all(isinstance(v, (int, float)) for v in value):
                    dynamo_item[key] = {'NS': [str(v) for v in value]}
                else:
                    # Liste complexe, stocker comme JSON
                    dynamo_item[key] = {'S': json.dumps(value, ensure_ascii=False)}
            else:
                # Fallback: convertir en string
                dynamo_item[key] = {'S': str(value)}
        
        return dynamo_item
    
    def get_invoice(self, invoice_id: str) -> Optional[Dict[str, Any]]:
        """
        Récupère une facture par son ID
        
        Args:
            invoice_id: ID de la facture
            
        Returns:
            Données de la facture ou None
        """
        try:
            response = self.client.get_item(
                TableName=self.table_name,
                Key={'invoice_id': {'S': invoice_id}}
            )
            
            item = response.get('Item')
            if not item:
                return None
            
            # Convertir depuis le format DynamoDB
            return self._convert_from_dynamo_format(item)
            
        except ClientError as e:
            logger.error(f"Erreur lors de la récupération: {str(e)}")
            return None
    
    def _convert_from_dynamo_format(self, dynamo_item: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Convertit du format DynamoDB vers Python
        
        Args:
            dynamo_item: Item DynamoDB
            
        Returns:
            Item Python
        """
        item = {}
        
        for key, value_dict in dynamo_item.items():
            if 'S' in value_dict:
                item[key] = value_dict['S']
            elif 'N' in value_dict:
                # Essayer de convertir en int ou float
                num_str = value_dict['N']
                try:
                    if '.' in num_str:
                        item[key] = float(num_str)
                    else:
                        item[key] = int(num_str)
                except ValueError:
                    item[key] = num_str
            elif 'BOOL' in value_dict:
                item[key] = value_dict['BOOL']
            elif 'M' in value_dict:
                item[key] = self._convert_from_dynamo_format(value_dict['M'])
            elif 'SS' in value_dict:
                item[key] = value_dict['SS']
            elif 'NS' in value_dict:
                item[key] = [float(n) if '.' in n else int(n) for n in value_dict['NS']]
            elif 'NULL' in value_dict:
                item[key] = None
        
        # Parser les données brutes si présentes
        if 'raw_data' in item:
            try:
                item['parsed_data'] = json.loads(item['raw_data'])
            except json.JSONDecodeError:
                item['parsed_data'] = {}
        
        return item
    
    def query_by_invoice_number(self, invoice_number: str) -> List[Dict[str, Any]]:
        """
        Recherche des factures par numéro de facture
        
        Args:
            invoice_number: Numéro de facture
            
        Returns:
            Liste des factures correspondantes
        """
        try:
            response = self.client.query(
                TableName=self.table_name,
                IndexName='numero_facture-index',
                KeyConditionExpression='numero_facture = :inv_num',
                ExpressionAttributeValues={
                    ':inv_num': {'S': invoice_number}
                }
            )
            
            items = response.get('Items', [])
            return [self._convert_from_dynamo_format(item) for item in items]
            
        except ClientError as e:
            logger.error(f"Erreur lors de la requête: {str(e)}")
            return []
    
    def query_by_supplier(self, supplier: str) -> List[Dict[str, Any]]:
        """
        Recherche des factures par fournisseur
        
        Args:
            supplier: Nom du fournisseur
            
        Returns:
            Liste des factures correspondantes
        """
        try:
            response = self.client.query(
                TableName=self.table_name,
                IndexName='fournisseur-index',
                KeyConditionExpression='fournisseur = :supp',
                ExpressionAttributeValues={
                    ':supp': {'S': supplier}
                }
            )
            
            items = response.get('Items', [])
            return [self._convert_from_dynamo_format(item) for item in items]
            
        except ClientError as e:
            logger.error(f"Erreur lors de la requête: {str(e)}")
            return []
    
    def query_by_date_range(self, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """
        Recherche des factures par plage de dates
        
        Args:
            start_date: Date de début (YYYY-MM-DD)
            end_date: Date de fin (YYYY-MM-DD)
            
        Returns:
            Liste des factures correspondantes
        """
        try:
            # Note: Cette requête nécessite un scan car nous n'avons pas d'index sur la plage de dates
            # Pour de meilleures performances, envisagez d'ajouter un index composite
            response = self.client.scan(
                TableName=self.table_name,
                FilterExpression='date_facture BETWEEN :start AND :end',
                ExpressionAttributeValues={
                    ':start': {'S': start_date},
                    ':end': {'S': end_date}
                }
            )
            
            items = response.get('Items', [])
            return [self._convert_from_dynamo_format(item) for item in items]
            
        except ClientError as e:
            logger.error(f"Erreur lors du scan: {str(e)}")
            return []
    
    def delete_invoice(self, invoice_id: str) -> bool:
        """
        Supprime une facture
        
        Args:
            invoice_id: ID de la facture
            
        Returns:
            True si la suppression a réussi
        """
        try:
            self.client.delete_item(
                TableName=self.table_name,
                Key={'invoice_id': {'S': invoice_id}}
            )
            
            logger.info(f"Facture {invoice_id} supprimée")
            return True
            
        except ClientError as e:
            logger.error(f"Erreur lors de la suppression: {str(e)}")
            return False
