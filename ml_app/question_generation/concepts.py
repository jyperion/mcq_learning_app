from typing import Dict, List

# Define valid ML concepts and their associated keywords
VALID_CONCEPTS: Dict[str, List[str]] = {
    "Machine Learning Basics": [
        "supervised learning", "unsupervised learning", "classification",
        "regression", "clustering", "bias", "variance", "overfitting",
        "underfitting", "cross-validation", "feature selection"
    ],
    "Deep Learning": [
        "neural networks", "backpropagation", "activation functions",
        "convolutional", "recurrent", "transformer", "attention mechanism",
        "transfer learning", "fine-tuning", "embeddings"
    ],
    "Natural Language Processing": [
        "tokenization", "word embeddings", "language models", "sentiment analysis",
        "named entity recognition", "machine translation", "text classification",
        "sequence-to-sequence", "BERT", "GPT"
    ],
    "Computer Vision": [
        "image classification", "object detection", "segmentation",
        "feature extraction", "CNN", "ResNet", "YOLO", "face recognition",
        "image generation", "GANs"
    ],
    "Model Optimization": [
        "gradient descent", "learning rate", "batch size", "momentum",
        "Adam", "RMSprop", "regularization", "dropout", "batch normalization",
        "hyperparameter tuning"
    ],
    "Model Evaluation": [
        "accuracy", "precision", "recall", "F1 score", "ROC curve",
        "AUC", "confusion matrix", "cross-validation", "validation set",
        "test set"
    ],
    "MLOps": [
        "model deployment", "model monitoring", "model versioning",
        "CI/CD", "A/B testing", "feature store", "model registry",
        "data versioning", "experiment tracking", "model serving"
    ]
}

def identify_concept(text: str) -> str:
    """Identify the ML concept from text based on keyword matching"""
    text = text.lower()
    max_matches = 0
    identified_concept = "Machine Learning Basics"  # default

    for concept, keywords in VALID_CONCEPTS.items():
        matches = sum(1 for keyword in keywords if keyword.lower() in text)
        if matches > max_matches:
            max_matches = matches
            identified_concept = concept

    return identified_concept

def get_all_concepts() -> List[str]:
    """Get a list of all valid concepts"""
    return list(VALID_CONCEPTS.keys())

def get_concept_keywords(concept: str) -> List[str]:
    """Get keywords for a specific concept"""
    return VALID_CONCEPTS.get(concept, [])
