import logging
from abc import ABC, abstractmethod
from typing import Optional
from app.services.video_pipeline.context import VideoContext

class BaseStep(ABC):
    """Base class for all pipeline steps.
    
    All pipeline steps should inherit from this class and implement the process method.
    Each step should handle a specific part of the video processing workflow.
    """
    
    def __init__(self, name: str, enabled: bool = True):
        """Initialize the step.
        
        Args:
            name: The name of the step
            enabled: Whether the step is enabled by default
        """
        self.name = name
        self.enabled = enabled
        self.logger = logging.getLogger(f"video_pipeline.{name}")
    
    def __call__(self, context: VideoContext) -> VideoContext:
        """Make the step callable.
        
        This method handles common logic like checking if the step is enabled
        before delegating to the actual process method.
        
        Args:
            context: The video context to process
            
        Returns:
            The updated video context
        """
        if not self.enabled:
            self.logger.info(f"Step {self.name} is disabled, skipping")
            return context
        
        if context.has_errors():
            self.logger.info(f"Skipping step {self.name} due to previous errors")
            return context
        
        self.logger.info(f"Running step {self.name}")
        try:
            return self.process(context)
        except Exception as e:
            error_msg = f"Error in step {self.name}: {str(e)}"
            self.logger.error(error_msg)
            context.add_error(error_msg)
            return context
    
    @abstractmethod
    def process(self, context: VideoContext) -> VideoContext:
        """Process the video context.
        
        This method should be implemented by all subclasses to perform
        the actual processing logic for the step.
        
        Args:
            context: The video context to process
            
        Returns:
            The updated video context
        """
        pass

class NonCriticalStep(BaseStep):
    """Base class for non-critical pipeline steps.
    
    Non-critical steps will continue to run even if the context has errors from previous steps.
    This is useful for steps like collage creation that can run independently of other steps.
    """
    
    def __call__(self, context: VideoContext) -> VideoContext:
        """Make the step callable.
        
        This method handles common logic like checking if the step is enabled
        before delegating to the actual process method. It does NOT skip on previous errors.
        
        Args:
            context: The video context to process
            
        Returns:
            The updated video context
        """
        if not self.enabled:
            self.logger.info(f"Step {self.name} is disabled, skipping")
            return context
        
        # This step will run even if there are previous errors
        
        self.logger.info(f"Running step {self.name} (even with previous errors)")
        try:
            return self.process(context)
        except Exception as e:
            error_msg = f"Error in step {self.name}: {str(e)}"
            self.logger.error(error_msg)
            context.add_error(error_msg)
            return context 