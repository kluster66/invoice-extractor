#!/usr/bin/env python3
"""
Liste les modèles Bedrock disponibles dans la région
"""

import boto3
from config.config import Config

def list_available_models():
    """Liste les modèles disponibles"""
    print("Liste des modèles Bedrock disponibles dans", Config.AWS_REGION)
    print("=" * 80)
    
    bedrock = boto3.client('bedrock', region_name=Config.AWS_REGION)
    
    try:
        # Lister les fondations de modèles
        response = bedrock.list_foundation_models()
        
        models_by_provider = {}
        for model in response.get('modelSummaries', []):
            provider = model.get('providerName', 'Unknown')
            model_id = model.get('modelId', 'Unknown')
            model_name = model.get('modelName', 'Unknown')
            
            if provider not in models_by_provider:
                models_by_provider[provider] = []
            
            models_by_provider[provider].append({
                'modelId': model_id,
                'modelName': model_name,
                'inputModalities': model.get('inputModalities', []),
                'outputModalities': model.get('outputModalities', []),
                'customizationsSupported': model.get('customizationsSupported', [])
            })
        
        # Afficher par provider
        total_models = 0
        for provider, models in models_by_provider.items():
            print(f'\n{provider}:')
            print('-' * 60)
            for model in models:
                print(f'  {model["modelId"]}')
                print(f'    Nom: {model["modelName"]}')
                print(f'    Entrée: {model["inputModalities"]} | Sortie: {model["outputModalities"]}')
                if model['customizationsSupported']:
                    print(f'    Customisations: {model["customizationsSupported"]}')
                print()
                total_models += 1
        
        print(f'\n{"="*80}')
        print(f'Total: {total_models} modèles disponibles dans {Config.AWS_REGION}')
        
        # Suggestions pour l'extraction de factures
        print(f'\n{"="*80}')
        print('SUGGESTIONS POUR L\'EXTRACTION DE FACTURES:')
        print('=' * 80)
        
        print('\n1. Modèles recommandés (par ordre de préférence):')
        recommendations = []
        
        for provider, models in models_by_provider.items():
            for model in models:
                model_id = model['modelId']
                model_name = model['modelName']
                
                # Critères de recommandation
                if 'TEXT' in model['inputModalities'] and 'TEXT' in model['outputModalities']:
                    if 'anthropic' in model_id.lower():
                        if 'claude-3' in model_id.lower():
                            if 'sonnet' in model_id.lower():
                                recommendations.append(('★★★★★', model_id, 'Claude 3 Sonnet - Meilleure précision'))
                            elif 'haiku' in model_id.lower():
                                recommendations.append(('★★★★☆', model_id, 'Claude 3 Haiku - Rapide et économique'))
                            elif 'opus' in model_id.lower():
                                recommendations.append(('★★★★☆', model_id, 'Claude 3 Opus - Très puissant'))
                    
                    elif 'amazon.titan' in model_id.lower():
                        if 'text' in model_id.lower():
                            recommendations.append(('★★★☆☆', model_id, 'Amazon Titan - Natif AWS'))
                    
                    elif 'meta.llama' in model_id.lower():
                        if '3' in model_id.lower():
                            recommendations.append(('★★★☆☆', model_id, 'Meta Llama 3 - Open source'))
        
        # Trier et afficher les recommandations
        if recommendations:
            for stars, model_id, description in sorted(recommendations, key=lambda x: x[0], reverse=True):
                print(f'  {stars} {model_id:60} - {description}')
        else:
            print('  Aucun modèle recommandé trouvé')
        
        print('\n2. Étapes pour activer un modèle:')
        print('   a. AWS Console > Bedrock > Model access')
        print('   b. Sélectionner le modèle souhaité')
        print('   c. Remplir le formulaire de cas d\'utilisation')
        print('   d. Attendre l\'approbation (généralement rapide)')
        
        print('\n3. Configuration rapide:')
        print('   Pour utiliser un modèle, ajoutez dans .env:')
        print('   BEDROCK_MODEL_ID=votre_modele_id')
        
    except Exception as e:
        print(f'Erreur: {e}')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    list_available_models()
