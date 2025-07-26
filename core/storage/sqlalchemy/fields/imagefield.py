import io
from typing import Optional, Union
from PIL import Image as PILImage

from core.exceptions.request import InvalidRequestException
from core.storage.sqlalchemy.fields.abstract import AbstractFileField
from core.storage.storage_class.abstract import Storage


class Image(dict):
    """
    A dictionary-like object representing an image and its available variations.
    It provides convenient access to the URLs of the original image and its
    generated variants, as well as their respective file paths.

    This class is primarily used as the return type for `ImageField.get_result()`.
    """

    def __init__(self, storage: Storage, variations: dict, **kwargs):
        """
        Initializes the Image object.

        Args:
            storage (Storage): The storage instance used to retrieve URLs.
            variations (dict): A dictionary mapping variation names to their
                               corresponding file paths in storage.
            **kwargs: Keyword arguments representing the actual URLs of the
                      original and variant images (e.g., 'original'='http://...',
                      'thumbnail'='http://...').
        """
        self.variations = variations  # Stores file paths for variations
        self.storage = storage
        super().__init__(kwargs)  # Stores URLs for variations

    def __getattr__(self, item):
        """
        Allows access to image URLs as attributes.
        For example, `image.original` will return the URL for the original image.
        """
        if self.variations["original"].startswith("http://") or self.variations[
            "original"
        ].startswith("https://"):
            return self.variations.get("original")
        return super().__getattr__(item)  # Ensure dict methods work

    def get(self, item, **kwargs):
        """
        Allows access to image URLs as attributes.
        For example, `image.original` will return the URL for the original image.
        """
        if self.variations["original"].startswith("http://") or self.variations[
            "original"
        ].startswith("https://"):
            return self.variations.get("original")
        return super().get(item, **kwargs)  # Ensure dict methods work

    def delete(self):
        raise NotImplementedError("Image does not support direct delete operation. ")


class ImageField(AbstractFileField):
    """
    A custom SQLAlchemy field designed for efficient image handling with S3-compatible
    object storage. This field stores only the original image file's path in the
    database and generates specified image variations (e.g., thumbnails, resized
    versions) on demand during the upload process.

    It extends `AbstractFileField`, providing specialized functionalities for
    image validation, processing, and variation generation.
    """

    def __init__(
        self,
        storage: Storage = None,
        upload_to: str = "uploads",
        max_size: int = 10 * 1024 * 1024,
        allowed_extensions: list[str] = ["jpg", "jpeg", "png", "gif", "webp"],
        variations: dict = {},
    ):
        """
        Initializes the ImageField.

        Args:
            storage (Storage): An instance of a storage class (e.g., S3Storage)
                               responsible for handling file operations (save, get_url).
            upload_to (str, optional): The base directory within the storage
                                       where images will be uploaded. Defaults to "uploads".
            max_size (int, optional): The maximum allowed size for the original
                                      image file in bytes. Defaults to 10 MB.
            allowed_extensions (list[str], optional): A list of allowed file
                                                      extensions for image uploads.
                                                      Defaults to common web image formats.
            variations (dict, optional): A dictionary defining the image variations
                                         to be generated. Each key represents the
                                         variation name, and its value is a dictionary
                                         specifying 'width' and 'height' for resizing.
                                         Example: `{'thumbnail': {'width': 150, 'height': 150}}`.
        """
        super().__init__(storage, upload_to)
        self.allowed_extensions = allowed_extensions
        self.variations = variations
        self.max_size = max_size

    def _process_image_file(
        self, image_data: Union[bytes, io.BytesIO], path: Optional[str] = None
    ) -> tuple[PILImage.Image, str]:
        """
        Processes raw image data (bytes or BytesIO) into a PIL Image object
        and determines its format. Performs basic format validation against
        `allowed_extensions`.

        Args:
            image_data (Union[bytes, io.BytesIO]): The raw image data.
            path (Optional[str]): The intended file path (used for context, though
                                  not directly used for processing in this method).

        Returns:
            tuple[PILImage.Image, str]: A tuple containing the PIL Image object
                                        and its detected format (e.g., 'jpeg', 'png').

        Raises:
            ValueError: If the image format cannot be determined.
            InvalidRequestException: If the image format is not in `allowed_extensions`.
        """
        if isinstance(image_data, io.BytesIO):
            img = PILImage.open(image_data)
        else:
            img = PILImage.open(io.BytesIO(image_data))

        if not img.format:
            raise ValueError("Invalid image format: Could not determine format.")

        fmt = img.format.lower()

        if self.allowed_extensions and fmt not in self.allowed_extensions:
            raise InvalidRequestException(
                message=f"Unsupported image format. Allowed formats: {', '.join(self.allowed_extensions)}",
            )

        return img, fmt

    def _generate_variants(
        self, image: PILImage.Image, variations: dict
    ) -> dict[str, PILImage.Image]:
        """
        Generates resized image variants based on the defined `variations` dictionary.
        Images are resized using LANCZOS resampling for high quality.

        Args:
            image (PILImage.Image): The original PIL Image object.
            variations (dict): A dictionary defining the desired variations,
                               with 'width' and 'height' for each.

        Returns:
            dict[str, PILImage.Image]: A dictionary where keys are variation names
                                       and values are the generated PIL Image variant objects.
        """

        def resize_image(
            img: PILImage.Image, width: int, height: int
        ) -> PILImage.Image:
            """Helper function to resize an image, maintaining aspect ratio."""
            img_ratio = img.width / img.height
            target_ratio = width / height

            if img_ratio > target_ratio:
                # Image is wider than target aspect ratio, fit by target width
                new_width = width
                new_height = round(width / img_ratio)
            else:
                # Image is taller than or matches target aspect ratio, fit by target height
                new_height = height
                new_width = round(height * img_ratio)

            return img.resize((new_width, new_height), PILImage.LANCZOS)

        variants = {}
        for key, value in variations.items():
            width = value.get("width")
            height = value.get("height")
            # Only generate variant if both width and height are specified
            if width is not None and height is not None:
                variants[key] = resize_image(image, width, height)

        return variants

    def _get_variant_path(self, path: str, key: str) -> str:
        """
        Constructs the file path for an image variant by embedding the variant key
        before the file extension (e.g., 'image.thumbnail.jpg').

        Args:
            path (str): The original image's file path.
            key (str): The key representing the variation (e.g., 'thumbnail', 'medium').

        Returns:
            str: The generated file path for the image variant.
        """
        if "." in path:
            ext = path.split(".")[-1]
            file_name = ".".join(path.split(".")[:-1])
        else:
            ext = ""  # No extension, append key directly
            file_name = path
        return f"{file_name}.{key}.{ext}" if ext else f"{file_name}.{key}"

    def save_file(self, content: Union[bytes, io.BytesIO], path: str):
        """
        Saves the original image and generates/saves its specified variations
        to the configured storage. Performs size validation before saving.

        This method is typically called by the SQLAlchemy ORM during an object's
        save operation when the ImageField is updated with new content.

        Args:
            content (Union[bytes, io.BytesIO]): The raw content of the image file.
            path (str): The desired storage path for the original image file.

        Raises:
            InvalidRequestException: If the image size exceeds `max_size` after processing.
            (Other exceptions from `_process_image_file` or `storage.save` may also occur).
        """
        img, fmt = self._process_image_file(content, path)
        buffer = io.BytesIO()
        img.save(buffer, format=fmt)
        buffer.seek(0)  # Rewind buffer to the beginning for reading

        if self.max_size and buffer.getbuffer().nbytes > self.max_size:
            raise InvalidRequestException(
                f"Image size ({buffer.getbuffer().nbytes} bytes) exceeds maximum allowed size of {self.max_size} bytes."
            )

        # Save the original image
        self.storage.save(
            content=buffer,
            filepath=path,
            content_type=f"image/{fmt}",
        )

        if self.variations:
            # Generate and save image variants
            variants = self._generate_variants(img, self.variations)
            for key, variant in variants.items():
                buffer = io.BytesIO()
                # Save variant in the same format as the original
                variant.save(buffer, format=fmt)
                buffer.seek(0)

                variant_path = self._get_variant_path(path, key)

                # Avoid overwriting the original if a variant key matches the original path logic
                if variant_path != path:
                    self.storage.save(
                        content=buffer,
                        filepath=variant_path,
                        content_type=f"image/{fmt}",
                    )

    def get_result(self, path: str) -> "Image":
        """
        Retrieves the URLs for the original image and all its generated variations.
        This method constructs an `Image` object containing URLs to access the
        stored image files.

        Args:
            path (str): The storage path of the original image file as stored in the database.

        Returns:
            Image: An `Image` object containing URLs for the original and all
                   available variations. Each key in the `Image` object corresponds
                   to a variation name (e.g., 'original', 'thumbnail') and its value
                   is the public URL.
        """
        if not path:
            return None
        variations = {}
        variation_paths = {}

        if path.startswith("http://") or path.startswith("https://"):
            # If the path is already a URL, use it directly
            variations["original"] = path
            variation_paths["original"] = path
        else:
            # Get URLs for all defined variations
            for variation_key in self.variations:
                variant_path = self._get_variant_path(path, variation_key)
                variation_paths[variation_key] = variant_path
                try:
                    url = self.storage.get_url(variant_path)
                    variations[variation_key] = url
                except Exception:
                    # Gracefully handle cases where a variant might not exist
                    # (e.g., if generation failed or it was manually deleted)
                    pass

            # Always include the original image
            variations["original"] = self.storage.get_url(path)
            variation_paths["original"] = path

        # Return a specialized Image object for easier access to URLs and paths
        return Image(storage=self.storage, variations=variation_paths, **variations)
