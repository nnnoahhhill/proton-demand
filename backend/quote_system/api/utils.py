# api/utils.py

import os
import tempfile
import logging
import httpx
from fastapi import HTTPException
from starlette import status

logger = logging.getLogger(__name__)

# Define supported file extensions (align with processors)
SUPPORTED_FILE_EXTENSIONS = [".stl", ".3mf", ".obj"] # Add more as needed
MAX_FILE_SIZE_MB = 100 # Example: Set a reasonable max file size

async def download_file(url: str, target_dir: str) -> str:
    """
    Downloads a file from a given URL to a target directory.

    Args:
        url: The URL of the file to download.
        target_dir: The directory to save the downloaded file.

    Returns:
        The full path to the downloaded file.

    Raises:
        HTTPException: If download fails, file type is unsupported, or size exceeds limit.
    """
    logger.info(f"Attempting to download file from: {url}")
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=60.0) as client:
            # Use a streaming response to handle potentially large files
            async with client.stream("GET", url) as response:
                response.raise_for_status() # Raise exception for 4xx/5xx status codes

                # Check Content-Length header (if available)
                content_length = response.headers.get("Content-Length")
                if content_length:
                    file_size = int(content_length)
                    if file_size > MAX_FILE_SIZE_MB * 1024 * 1024:
                        logger.error(f"File size ({file_size} bytes) exceeds limit ({MAX_FILE_SIZE_MB} MB).")
                        raise HTTPException(
                            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                            detail=f"File size exceeds the maximum limit of {MAX_FILE_SIZE_MB} MB."
                        )
                    logger.debug(f"File size from header: {file_size} bytes.")
                else:
                    logger.warning("Content-Length header not found. Cannot pre-check file size limit.")

                # Determine filename and validate extension
                # Try to get filename from Content-Disposition header first
                content_disposition = response.headers.get("Content-Disposition")
                filename = None
                if content_disposition:
                    parts = content_disposition.split('filename=')
                    if len(parts) > 1:
                        filename = parts[1].strip('"\' ')

                # If not in header, extract from URL path
                if not filename:
                     filename = os.path.basename(urlparse(url).path)
                     if not filename:
                         # Fallback if URL path is weird (e.g., root)
                         filename = f"downloaded_file_{uuid.uuid4()[:8]}"
                         logger.warning(f"Could not determine filename, using fallback: {filename}")

                _, file_extension = os.path.splitext(filename)
                file_extension = file_extension.lower()

                if file_extension not in SUPPORTED_FILE_EXTENSIONS:
                    logger.error(f"Unsupported file extension: {file_extension}")
                    raise HTTPException(
                        status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                        detail=f"Unsupported file type '{file_extension}'. Supported types: {SUPPORTED_FILE_EXTENSIONS}"
                    )

                # Ensure filename is safe
                # Basic sanitization, consider more robust library if needed
                safe_filename = "".join(c for c in filename if c.isalnum() or c in ('.', '-', '_'))
                if not safe_filename:
                    safe_filename = f"file{file_extension}" # Minimal safe name

                file_path = os.path.join(target_dir, safe_filename)

                # Download and save the file chunk by chunk
                downloaded_size = 0
                with open(file_path, "wb") as f:
                    async for chunk in response.aiter_bytes():
                        f.write(chunk)
                        downloaded_size += len(chunk)
                        # Check size limit again if Content-Length wasn't present
                        if not content_length and downloaded_size > MAX_FILE_SIZE_MB * 1024 * 1024:
                            f.close() # Close the file before deleting
                            os.remove(file_path) # Clean up partial download
                            logger.error(f"Downloaded size ({downloaded_size} bytes) exceeded limit ({MAX_FILE_SIZE_MB} MB) during streaming.")
                            raise HTTPException(
                                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                                detail=f"File size exceeded the maximum limit of {MAX_FILE_SIZE_MB} MB during download."
                            )

                logger.info(f"File successfully downloaded to: {file_path} ({downloaded_size} bytes)")
                return file_path

    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error downloading file from {url}: {e.response.status_code} - {e.response.text}")
        status_code = status.HTTP_400_BAD_REQUEST
        detail = f"Failed to download file. Server responded with {e.response.status_code}."
        if e.response.status_code == 404:
            status_code = status.HTTP_404_NOT_FOUND
            detail = "File not found at the provided URL."
        elif 500 <= e.response.status_code < 600:
            status_code = status.HTTP_502_BAD_GATEWAY
            detail = f"Failed to download file. Remote server returned an error ({e.response.status_code})."

        raise HTTPException(status_code=status_code, detail=detail)
    except httpx.RequestError as e:
        logger.error(f"Network error downloading file from {url}: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Network error occurred while trying to download the file: {e}"
        )
    except IOError as e:
        logger.error(f"Error saving downloaded file to {target_dir}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not save the downloaded file to disk."
        )
    except HTTPException: # Re-raise specific HTTPExceptions raised earlier
         raise
    except Exception as e:
        logger.exception(f"Unexpected error downloading file from {url}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred during file download: {e}"
        )

# Need these imports for the code above
from urllib.parse import urlparse
import uuid
