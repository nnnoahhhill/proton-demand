# core/exceptions.py

class ManufacturingQuoteError(Exception):
    """Base class for all custom exceptions in this application."""
    pass

class ConfigurationError(ManufacturingQuoteError):
    """Exception raised for errors in configuration loading or validation."""
    pass

class FileFormatError(ManufacturingQuoteError):
    """Exception raised for unsupported or invalid input file formats."""
    pass

class GeometryProcessingError(ManufacturingQuoteError):
    """Exception raised during mesh loading, analysis, or manipulation."""
    pass

class StepConversionError(GeometryProcessingError):
    """Specific exception for failures during STEP to STL conversion."""
    pass

class DFMCheckError(ManufacturingQuoteError):
    """Exception raised if a specific DFM check encounters an error during execution."""
    pass

class SlicerError(ManufacturingQuoteError):
    """Exception raised for errors related to external slicer execution or parsing."""
    pass

class MaterialNotFoundError(ManufacturingQuoteError):
    """Exception raised when a specified material ID cannot be found for a process."""
    pass

class QuoteGenerationError(ManufacturingQuoteError):
    """Generic exception for failures during the overall quote generation pipeline."""
    pass

class SlicerExecutionError(ManufacturingQuoteError):
    """Error occurred during slicer execution (e.g., process failed, timeout)."""
    pass

# Add more specific exceptions as needed, e.g., CncFeatureRecognitionError etc. 