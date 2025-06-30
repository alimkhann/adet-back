import os
import uuid
from io import BytesIO
from typing import Optional, Tuple, Dict, Any
from PIL import Image, ExifTags
import logging
from .redis_service import redis_service

logger = logging.getLogger(__name__)

class MediaService:
    def __init__(self):
        self.supported_image_formats = {'JPEG', 'PNG', 'WEBP'}
        self.max_image_size = 10 * 1024 * 1024  # 10MB
        self.max_video_size = 50 * 1024 * 1024  # 50MB

    # MARK: - Image Processing

    def compress_image(
        self,
        image_data: bytes,
        max_file_size: int = 2_000_000,  # 2MB default
        quality: int = 85,
        max_dimension: int = 1080
    ) -> Optional[Tuple[bytes, Dict[str, Any]]]:
        """
        Compress image with specified constraints
        Returns tuple of (compressed_data, metadata) or None if failed
        """
        try:
            # Open image
            image = Image.open(BytesIO(image_data))

            # Preserve original metadata
            original_format = image.format
            original_size = len(image_data)
            original_dimensions = image.size

            # Fix orientation based on EXIF data
            image = self._fix_image_orientation(image)

            # Resize if needed
            image = self._resize_image(image, max_dimension)

            # Convert to RGB if necessary (for JPEG compression)
            if image.mode in ('RGBA', 'P'):
                background = Image.new('RGB', image.size, (255, 255, 255))
                if image.mode == 'P':
                    image = image.convert('RGBA')
                background.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
                image = background

            # Compress with decreasing quality until size requirement is met
            current_quality = quality
            while current_quality > 20:
                output = BytesIO()
                image.save(output, format='JPEG', quality=current_quality, optimize=True)
                compressed_data = output.getvalue()

                if len(compressed_data) <= max_file_size or current_quality <= 20:
                    break

                current_quality -= 10

            # Generate metadata
            metadata = {
                'original_size': original_size,
                'compressed_size': len(compressed_data),
                'original_dimensions': original_dimensions,
                'compressed_dimensions': image.size,
                'original_format': original_format,
                'final_quality': current_quality,
                'compression_ratio': round(len(compressed_data) / original_size, 3)
            }

            logger.info(f"Image compressed: {original_size} -> {len(compressed_data)} bytes "
                       f"({metadata['compression_ratio']}x compression)")

            return compressed_data, metadata

        except Exception as e:
            logger.error(f"Failed to compress image: {e}")
            return None

    def _fix_image_orientation(self, image: Image.Image) -> Image.Image:
        """Fix image orientation based on EXIF data"""
        try:
            if hasattr(image, '_getexif'):
                exif = image._getexif()
                if exif is not None:
                    for tag, value in exif.items():
                        if tag in ExifTags.TAGS and ExifTags.TAGS[tag] == 'Orientation':
                            if value == 3:
                                image = image.rotate(180, expand=True)
                            elif value == 6:
                                image = image.rotate(270, expand=True)
                            elif value == 8:
                                image = image.rotate(90, expand=True)
                            break
        except Exception as e:
            logger.warning(f"Could not fix image orientation: {e}")

        return image

    def _resize_image(self, image: Image.Image, max_dimension: int) -> Image.Image:
        """Resize image while maintaining aspect ratio"""
        width, height = image.size

        if width <= max_dimension and height <= max_dimension:
            return image

        # Calculate new dimensions
        if width > height:
            new_width = max_dimension
            new_height = int((height * max_dimension) / width)
        else:
            new_height = max_dimension
            new_width = int((width * max_dimension) / height)

        # Use high-quality resampling
        return image.resize((new_width, new_height), Image.Resampling.LANCZOS)

    # MARK: - Profile Image Processing

    def compress_profile_image(self, image_data: bytes) -> Optional[Tuple[bytes, Dict[str, Any]]]:
        """Compress profile image with specific settings"""
        return self.compress_image(
            image_data=image_data,
            max_file_size=500_000,  # 500KB
            quality=90,
            max_dimension=512  # Profile images don't need to be huge
        )

    # MARK: - Post Image Processing

    def compress_post_image(self, image_data: bytes) -> Optional[Tuple[bytes, Dict[str, Any]]]:
        """Compress post image with specific settings"""
        return self.compress_image(
            image_data=image_data,
            max_file_size=2_000_000,  # 2MB
            quality=85,
            max_dimension=1080
        )

    # MARK: - Image Validation

    def validate_image(self, image_data: bytes) -> Tuple[bool, str]:
        """Validate image format and size"""
        if len(image_data) > self.max_image_size:
            return False, f"Image too large. Maximum size is {self.max_image_size // 1024 // 1024}MB"

        try:
            image = Image.open(BytesIO(image_data))
            if image.format not in self.supported_image_formats:
                return False, f"Unsupported format. Supported: {', '.join(self.supported_image_formats)}"

            # Check for reasonable dimensions
            width, height = image.size
            if width < 10 or height < 10:
                return False, "Image dimensions too small"
            if width > 10000 or height > 10000:
                return False, "Image dimensions too large"

            return True, "Valid image"

        except Exception as e:
            return False, f"Invalid image file: {str(e)}"

    # MARK: - Media URL Generation

    def generate_media_id(self) -> str:
        """Generate unique media ID"""
        return str(uuid.uuid4())

    def cache_media_url(self, media_id: str, url: str, ttl: int = 3600) -> bool:
        """Cache media URL in Redis"""
        return redis_service.cache_media_url(media_id, url, ttl)

    def get_cached_media_url(self, media_id: str) -> Optional[str]:
        """Get cached media URL from Redis"""
        return redis_service.get_cached_media_url(media_id)

    def cache_media_metadata(self, media_id: str, metadata: Dict[str, Any], ttl: int = 7200) -> bool:
        """Cache media metadata in Redis"""
        return redis_service.cache_media_metadata(media_id, metadata, ttl)

    def get_cached_media_metadata(self, media_id: str) -> Optional[Dict[str, Any]]:
        """Get cached media metadata from Redis"""
        return redis_service.get_cached_media_metadata(media_id)

    # MARK: - Content Validation

    def validate_content_limits(self, content_type: str, content: str) -> Tuple[bool, str]:
        """Validate content against defined limits"""
        limits = {
            'habit_name': 50,
            'habit_description': 200,
            'post_description': 280,
            'comment': 150,
            'user_bio': 150,
            'message': 1000,
            'username': 30,
            'display_name': 50
        }

        if content_type not in limits:
            return False, f"Unknown content type: {content_type}"

        max_length = limits[content_type]
        if len(content) > max_length:
            return False, f"Content too long. Maximum {max_length} characters allowed"

        return True, "Content valid"

    # MARK: - Utility Methods

    def get_image_info(self, image_data: bytes) -> Optional[Dict[str, Any]]:
        """Get basic image information"""
        try:
            image = Image.open(BytesIO(image_data))
            return {
                'format': image.format,
                'mode': image.mode,
                'size': image.size,
                'width': image.size[0],
                'height': image.size[1],
                'file_size': len(image_data)
            }
        except Exception as e:
            logger.error(f"Failed to get image info: {e}")
            return None

# Global media service instance
media_service = MediaService()