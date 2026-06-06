"""
Adorkable AI Model Training Module

Standalone training script for the clothing classifier.
Not used during inference - run this offline to train the model.
"""

import os
import json
from pathlib import Path
from typing import Tuple, Dict, List
import argparse

import numpy as np
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from sklearn.metrics import classification_report, confusion_matrix
import matplotlib.pyplot as plt
import seaborn as sns

from backend.config import (
    MODEL_PATH, CATEGORIES, STYLES, IMAGE_SIZE
)
from backend.ml.classifier import build_model, save_model


# =============================================================================
# Dataset Preparation
# =============================================================================

def prepare_dataset(
    dataset_path: str,
    validation_split: float = 0.2,
    batch_size: int = 32
) -> Tuple:
    """
    Prepare training and validation datasets from folder structure.
    
    Expected folder structure:
        dataset/
            category1/
                style1/
                    image1.jpg
                    image2.jpg
                style2/
                    ...
            category2/
                ...
    
    Args:
        dataset_path: Root path to dataset
        validation_split: Fraction for validation (0-1)
        batch_size: Batch size for training
        
    Returns:
        Tuple of (train_generator, val_generator, class_indices)
    """
    # Data augmentation for training
    train_datagen = ImageDataGenerator(
        rescale=1./255,
        rotation_range=20,
        width_shift_range=0.2,
        height_shift_range=0.2,
        shear_range=0.2,
        zoom_range=0.2,
        horizontal_flip=True,
        brightness_range=[0.8, 1.2],
        fill_mode='nearest',
        validation_split=validation_split
    )
    
    # Only rescaling for validation
    val_datagen = ImageDataGenerator(
        rescale=1./255,
        validation_split=validation_split
    )
    
    # Training generator
    train_generator = train_datagen.flow_from_directory(
        dataset_path,
        target_size=IMAGE_SIZE,
        batch_size=batch_size,
        class_mode='sparse',
        subset='training',
        shuffle=True
    )
    
    # Validation generator
    val_generator = val_datagen.flow_from_directory(
        dataset_path,
        target_size=IMAGE_SIZE,
        batch_size=batch_size,
        class_mode='sparse',
        subset='validation',
        shuffle=False
    )
    
    class_indices = train_generator.class_indices
    
    return train_generator, val_generator, class_indices


def prepare_multi_output_dataset(
    dataset_path: str,
    validation_split: float = 0.2,
    batch_size: int = 32
) -> Tuple:
    """
    Prepare dataset for multi-output classification (category + style).
    
    Expected structure:
        dataset/
            category_name/
                style_name/
                    image.jpg
    
    Args:
        dataset_path: Root path to dataset
        validation_split: Validation split ratio
        batch_size: Batch size
        
    Returns:
        Tuple of generators and index mappings
    """
    # Create mappings
    category_to_idx = {cat: i for i, cat in enumerate(CATEGORIES)}
    style_to_idx = {style: i for i, style in enumerate(STYLES)}
    
    # Custom generator for multi-output
    def create_generator(directory: str, subset: str, shuffle: bool = True):
        """Create a multi-output generator."""
        datagen = ImageDataGenerator(
            rescale=1./255,
            rotation_range=20,
            width_shift_range=0.2,
            height_shift_range=0.2,
            shear_range=0.2,
            zoom_range=0.2,
            horizontal_flip=True,
            brightness_range=[0.8, 1.2],
            fill_mode='nearest',
            validation_split=validation_split
        ) if subset == 'training' else ImageDataGenerator(
            rescale=1./255,
            validation_split=validation_split
        )
        
        # First get class labels
        base_generator = datagen.flow_from_directory(
            directory,
            target_size=IMAGE_SIZE,
            batch_size=batch_size,
            class_mode='sparse',
            subset=subset,
            shuffle=shuffle
        )
        
        # Parse class labels to extract category and style
        # Class label format: "category_style" or nested folders
        while True:
            batch_x, batch_y = next(base_generator)
            
            # Parse labels (this is simplified - real implementation would need
            # proper label extraction from directory structure)
            batch_category = []
            batch_style = []
            
            for label in batch_y:
                # Extract from label - this depends on your folder structure
                # Assuming labels are encoded as category_index * n_styles + style_index
                cat_idx = int(label) // len(STYLES)
                style_idx = int(label) % len(STYLES)
                batch_category.append(cat_idx)
                batch_style.append(style_idx)
            
            yield batch_x, {
                'category': np.array(batch_category),
                'style': np.array(batch_style)
            }
    
    train_gen = create_generator(dataset_path, 'training', shuffle=True)
    val_gen = create_generator(dataset_path, 'validation', shuffle=False)
    
    return train_gen, val_gen


# =============================================================================
# Training
# =============================================================================

def train(
    dataset_path: str,
    epochs: int = 20,
    batch_size: int = 32,
    learning_rate: float = 0.001,
    fine_tune: bool = False,
    fine_tune_epochs: int = 10
) -> keras.Model:
    """
    Train the clothing classifier model.
    
    Args:
        dataset_path: Path to training dataset
        epochs: Number of training epochs
        batch_size: Batch size
        learning_rate: Initial learning rate
        fine_tune: Whether to fine-tune the base model
        fine_tune_epochs: Additional epochs for fine-tuning
        
    Returns:
        Trained model
    """
    print("🚀 Starting model training...")
    print(f"   Dataset: {dataset_path}")
    print(f"   Epochs: {epochs}")
    print(f"   Batch size: {batch_size}")
    
    # Prepare data
    train_gen, val_gen, class_indices = prepare_dataset(
        dataset_path, batch_size=batch_size
    )
    
    print(f"   Classes found: {len(class_indices)}")
    print(f"   Training samples: {train_gen.samples}")
    print(f"   Validation samples: {val_gen.samples}")
    
    # Build model
    model = build_model()
    print("✅ Model built")
    
    # Callbacks
    callbacks = [
        keras.callbacks.EarlyStopping(
            monitor='val_loss',
            patience=5,
            restore_best_weights=True
        ),
        keras.callbacks.ReduceLROnPlateau(
            monitor='val_loss',
            factor=0.5,
            patience=3,
            min_lr=1e-7
        ),
        keras.callbacks.ModelCheckpoint(
            os.path.join(MODEL_PATH, 'best_model.h5'),
            monitor='val_accuracy',
            save_best_only=True
        )
    ]
    
    # Initial training
    print("\n📚 Phase 1: Training with frozen base...")
    history = model.fit(
        train_gen,
        epochs=epochs,
        validation_data=val_gen,
        callbacks=callbacks,
        verbose=1
    )
    
    # Fine-tuning (optional)
    if fine_tune:
        print("\n🔧 Phase 2: Fine-tuning...")
        
        # Unfreeze base model
        base_model = model.layers[1]  # MobileNetV2 is the second layer
        base_model.trainable = True
        
        # Recompile with lower learning rate
        model.compile(
            optimizer=keras.optimizers.Adam(learning_rate=learning_rate / 10),
            loss='sparse_categorical_crossentropy',
            metrics=['accuracy']
        )
        
        # Continue training
        history_fine = model.fit(
            train_gen,
            epochs=fine_tune_epochs,
            validation_data=val_gen,
            callbacks=callbacks,
            verbose=1
        )
        
        # Combine histories
        for key in history.history:
            history.history[key].extend(history_fine.history.get(key, []))
    
    # Save model
    save_model(model)
    
    # Save training history
    history_path = os.path.join(MODEL_PATH, 'training_history.json')
    with open(history_path, 'w') as f:
        json.dump(history.history, f)
    
    print("\n✅ Training complete!")
    
    return model, history


def train_multi_output(
    dataset_path: str,
    epochs: int = 20,
    batch_size: int = 32
) -> keras.Model:
    """
    Train multi-output model (category + style).
    
    Args:
        dataset_path: Path to dataset
        epochs: Number of epochs
        batch_size: Batch size
        
    Returns:
        Trained model
    """
    print("🚀 Starting multi-output model training...")
    
    train_gen, val_gen = prepare_multi_output_dataset(
        dataset_path, batch_size=batch_size
    )
    
    # Build model
    model = build_model()
    print("✅ Model built")
    
    # Callbacks
    callbacks = [
        keras.callbacks.EarlyStopping(
            monitor='val_category_loss',
            patience=5,
            restore_best_weights=True
        ),
        keras.callbacks.ReduceLROnPlateau(
            monitor='val_category_loss',
            factor=0.5,
            patience=3
        )
    ]
    
    # Train
    print("\n📚 Training...")
    history = model.fit(
        train_gen,
        epochs=epochs,
        validation_data=val_gen,
        callbacks=callbacks,
        verbose=1
    )
    
    # Save
    save_model(model)
    
    return model, history


# =============================================================================
# Evaluation
# =============================================================================

def evaluate_model(
    model: keras.Model,
    test_generator,
    save_results: bool = True
) -> Dict:
    """
    Evaluate model on test data.
    
    Args:
        model: Trained model
        test_generator: Test data generator
        save_results: Whether to save evaluation results
        
    Returns:
        Evaluation metrics dictionary
    """
    print("\n📊 Evaluating model...")
    
    # Get predictions
    test_generator.reset()
    predictions = model.predict(test_generator, verbose=1)
    predicted_classes = np.argmax(predictions, axis=1)
    
    # True labels
    true_classes = test_generator.classes
    class_labels = list(test_generator.class_indices.keys())
    
    # Calculate metrics
    results = {
        "accuracy": float(np.mean(predicted_classes == true_classes)),
        "total_samples": len(true_classes),
        "class_labels": class_labels
    }
    
    # Classification report
    report = classification_report(
        true_classes,
        predicted_classes,
        target_names=class_labels,
        output_dict=True
    )
    results["classification_report"] = report
    
    # Confusion matrix
    cm = confusion_matrix(true_classes, predicted_classes)
    results["confusion_matrix"] = cm.tolist()
    
    # Print summary
    print(f"\n📈 Accuracy: {results['accuracy']:.4f}")
    print("\nClassification Report:")
    print(classification_report(true_classes, predicted_classes, target_names=class_labels))
    
    # Save results
    if save_results:
        results_path = os.path.join(MODEL_PATH, 'evaluation_results.json')
        with open(results_path, 'w') as f:
            json.dump(results, f, indent=2)
        
        # Plot confusion matrix
        plt.figure(figsize=(10, 8))
        sns.heatmap(
            cm,
            annot=True,
            fmt='d',
            xticklabels=class_labels,
            yticklabels=class_labels,
            cmap='Blues'
        )
        plt.title('Confusion Matrix')
        plt.xlabel('Predicted')
        plt.ylabel('True')
        plt.tight_layout()
        plt.savefig(os.path.join(MODEL_PATH, 'confusion_matrix.png'))
        plt.close()
        
        print(f"\n✅ Results saved to {MODEL_PATH}")
    
    return results


def plot_training_history(history, save_path: str = None):
    """
    Plot training history.
    
    Args:
        history: Training history object
        save_path: Path to save plot
    """
    fig, axes = plt.subplots(1, 2, figsize=(12, 4))
    
    # Accuracy
    axes[0].plot(history.history['accuracy'], label='Train')
    axes[0].plot(history.history['val_accuracy'], label='Validation')
    axes[0].set_title('Model Accuracy')
    axes[0].set_xlabel('Epoch')
    axes[0].set_ylabel('Accuracy')
    axes[0].legend()
    axes[0].grid(True)
    
    # Loss
    axes[1].plot(history.history['loss'], label='Train')
    axes[1].plot(history.history['val_loss'], label='Validation')
    axes[1].set_title('Model Loss')
    axes[1].set_xlabel('Epoch')
    axes[1].set_ylabel('Loss')
    axes[1].legend()
    axes[1].grid(True)
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path)
        print(f"📊 Training history plot saved to {save_path}")
    else:
        plt.show()
    
    plt.close()


# =============================================================================
# Main Entry Point
# =============================================================================

def main():
    """Main training entry point."""
    parser = argparse.ArgumentParser(description='Train Adorkable AI Clothing Classifier')
    parser.add_argument('--dataset', type=str, required=True, help='Path to dataset')
    parser.add_argument('--epochs', type=int, default=20, help='Number of epochs')
    parser.add_argument('--batch-size', type=int, default=32, help='Batch size')
    parser.add_argument('--fine-tune', action='store_true', help='Enable fine-tuning')
    parser.add_argument('--multi-output', action='store_true', help='Train multi-output model')
    
    args = parser.parse_args()
    
    if args.multi_output:
        model, history = train_multi_output(
            args.dataset,
            epochs=args.epochs,
            batch_size=args.batch_size
        )
    else:
        model, history = train(
            args.dataset,
            epochs=args.epochs,
            batch_size=args.batch_size,
            fine_tune=args.fine_tune
        )
    
    # Plot history
    plot_path = os.path.join(MODEL_PATH, 'training_history.png')
    plot_training_history(history, save_path=plot_path)
    
    print("\n✅ Training complete! Model saved to:", MODEL_PATH)


if __name__ == "__main__":
    main()


# ✅ backend/ml/model_training.py generated — Adorkable AI
