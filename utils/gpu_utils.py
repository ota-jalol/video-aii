"""GPU memory management utilities."""

import torch
import gc
from typing import Optional
from utils.logging_utils import get_logger

logger = get_logger(__name__)


class GPUMemoryManager:
    """Manages GPU memory to prevent OOM errors."""
    
    def __init__(self, max_memory_gb: float = 12.0):
        """
        Initialize GPU memory manager.
        
        Args:
            max_memory_gb: Maximum GPU memory in GB
        """
        self.max_memory_gb = max_memory_gb
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
    
    def get_available_memory_gb(self) -> float:
        """
        Get available GPU memory in GB.
        
        Returns:
            Available memory in GB
        """
        if self.device == "cpu":
            return 0.0
        
        torch.cuda.empty_cache()
        return torch.cuda.get_device_properties(0).total_memory / (1024**3)
    
    def get_used_memory_gb(self) -> float:
        """
        Get used GPU memory in GB.
        
        Returns:
            Used memory in GB
        """
        if self.device == "cpu":
            return 0.0
        
        return torch.cuda.memory_allocated() / (1024**3)
    
    def get_free_memory_gb(self) -> float:
        """
        Get free GPU memory in GB.
        
        Returns:
            Free memory in GB
        """
        if self.device == "cpu":
            return 0.0
        
        return self.get_available_memory_gb() - self.get_used_memory_gb()
    
    def clear_cache(self) -> None:
        """Clear GPU cache and run garbage collection."""
        if self.device == "cuda":
            torch.cuda.empty_cache()
        gc.collect()
        logger.debug("GPU cache cleared")
    
    def check_memory_available(self, required_gb: float) -> bool:
        """
        Check if required memory is available.
        
        Args:
            required_gb: Required memory in GB
            
        Returns:
            True if memory is available
        """
        free_memory = self.get_free_memory_gb()
        available = free_memory >= required_gb
        
        if not available:
            logger.warning(
                f"Insufficient GPU memory. Required: {required_gb:.2f}GB, "
                f"Available: {free_memory:.2f}GB"
            )
        
        return available
    
    def log_memory_stats(self) -> None:
        """Log current GPU memory statistics."""
        if self.device == "cpu":
            logger.info("Running on CPU")
            return
        
        total = self.get_available_memory_gb()
        used = self.get_used_memory_gb()
        free = self.get_free_memory_gb()
        
        logger.info(
            f"GPU Memory - Total: {total:.2f}GB, "
            f"Used: {used:.2f}GB, Free: {free:.2f}GB"
        )


def cleanup_model(model: Optional[object]) -> None:
    """
    Clean up model from memory.
    
    Args:
        model: Model to clean up
    """
    if model is not None:
        del model
    
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    
    gc.collect()
    logger.debug("Model cleaned up from memory")


def get_device(prefer_gpu: bool = True) -> str:
    """
    Get the device to use for computation.
    
    Args:
        prefer_gpu: Whether to prefer GPU if available
        
    Returns:
        Device string ("cuda" or "cpu")
    """
    if prefer_gpu and torch.cuda.is_available():
        return "cuda"
    return "cpu"


def move_to_device(data: any, device: str) -> any:
    """
    Move data to specified device.
    
    Args:
        data: Data to move (tensor, model, etc.)
        device: Target device
        
    Returns:
        Data on target device
    """
    if hasattr(data, 'to'):
        return data.to(device)
    return data
