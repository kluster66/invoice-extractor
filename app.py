#!/usr/bin/env python3
"""
Application CDK pour déployer l'extracteur de factures
"""

import os
from aws_cdk import App
from infrastructure.cdk_stack import InvoiceExtractorStack

# Configuration
app = App()

# Créer la stack
stack = InvoiceExtractorStack(
    app, 
    "InvoiceExtractorStack",
    description="Stack pour l'extraction automatique de factures avec AWS Bedrock"
)

# Ajouter des tags
tags = {
    "Project": "InvoiceExtractor",
    "Environment": "Production",
    "Owner": "Maxtures",
    "Version": "2.0.0"
}

for key, value in tags.items():
    app.node.set_context(key, value)

# Synthétiser le template CloudFormation
app.synth()

print("✅ Application CDK prête !")
print("Commandes disponibles :")
print("  cdk synth     # Générer le template CloudFormation")
print("  cdk deploy    # Déployer la stack")
print("  cdk diff      # Voir les changements")
print("  cdk destroy   # Supprimer la stack")
