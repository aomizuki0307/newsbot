"""Hatena Fotolife image uploader using OAuth 1.0a"""

import base64
import logging
import os
import xml.etree.ElementTree as ET
from io import BytesIO
from typing import Optional

import requests
from requests_oauthlib import OAuth1

logger = logging.getLogger(__name__)

NS_ATOM = "http://www.w3.org/2005/Atom"
NS_DC = "http://purl.org/dc/elements/1.1/"

ET.register_namespace("", NS_ATOM)
ET.register_namespace("dc", NS_DC)


class HatenaFotolifeUploader:
    """Upload images to Hatena Fotolife via AtomPub API"""

    def __init__(
        self,
        consumer_key: Optional[str] = None,
        consumer_secret: Optional[str] = None,
        access_token: Optional[str] = None,
        access_token_secret: Optional[str] = None,
        post_uri: Optional[str] = None,
        folder: Optional[str] = None,
    ):
        """Initialize Hatena Fotolife uploader

        Args:
            consumer_key: OAuth consumer key
            consumer_secret: OAuth consumer secret
            access_token: OAuth access token
            access_token_secret: OAuth access token secret
            post_uri: Fotolife post URI
            folder: Target folder name
        """
        self.consumer_key = consumer_key or os.getenv("HATENA_OAUTH_CONSUMER_KEY")
        self.consumer_secret = consumer_secret or os.getenv("HATENA_OAUTH_CONSUMER_SECRET")
        self.access_token = access_token or os.getenv("HATENA_OAUTH_ACCESS_TOKEN")
        self.access_token_secret = access_token_secret or os.getenv("HATENA_OAUTH_ACCESS_TOKEN_SECRET")
        self.post_uri = post_uri or os.getenv("HATENA_FOTOLIFE_POST_URI", "https://f.hatena.ne.jp/atom/post")
        self.folder = folder or os.getenv("HATENA_FOTOLIFE_FOLDER", "Hatena Blog")

        if not all([self.consumer_key, self.consumer_secret, self.access_token, self.access_token_secret]):
            logger.warning("Hatena Fotolife OAuth credentials not fully configured")

    def _create_upload_xml(
        self,
        title: str,
        image_data: bytes,
        generator: str = "newsbot"
    ) -> bytes:
        """Create AtomPub XML for image upload

        Args:
            title: Image title
            image_data: Image binary data
            generator: Generator name

        Returns:
            XML as bytes
        """
        entry = ET.Element(ET.QName(NS_ATOM, "entry"))

        # Title
        title_el = ET.SubElement(entry, ET.QName(NS_ATOM, "title"))
        title_el.text = title

        # Content (base64-encoded image)
        content_el = ET.SubElement(entry, ET.QName(NS_ATOM, "content"))
        content_el.set("mode", "base64")
        content_el.set("type", "image/jpeg")
        content_el.text = base64.b64encode(image_data).decode('ascii')

        # Folder (dc:subject)
        if self.folder:
            subject_el = ET.SubElement(entry, ET.QName(NS_DC, "subject"))
            subject_el.text = self.folder

        # Generator
        generator_el = ET.SubElement(entry, ET.QName(NS_ATOM, "generator"))
        generator_el.text = generator

        return ET.tostring(entry, encoding="utf-8", xml_declaration=True)

    def _extract_image_info(self, response_text: str) -> Optional[dict]:
        """Extract image syntax and URL from Fotolife response

        Args:
            response_text: XML response from Fotolife

        Returns:
            Dict with syntax/url or None
        """
        try:
            root = ET.fromstring(response_text)

            syntax_value = None
            url_value = None

            # Look for hatena:syntax element (contains the [f:id:...] syntax)
            hatena_ns = "http://www.hatena.ne.jp/info/xmlns#"
            syntax_el = root.find(f".//{{{hatena_ns}}}syntax")

            if syntax_el is not None and syntax_el.text:
                syntax_value = syntax_el.text
                logger.info(f"Fotolife image syntax: {syntax_value}")

            # Fallback: extract from link rel="alternate"
            for link in root.findall(f"{{{NS_ATOM}}}link"):
                if link.attrib.get("rel") == "alternate":
                    href = link.attrib.get("href")
                    if href:
                        url_value = href
                        logger.info(f"Fotolife image URL: {url_value}")
                        break

            if not syntax_value and not url_value:
                logger.warning("Could not extract image info from Fotolife response")
                return None

            return {"syntax": syntax_value, "url": url_value}

        except ET.ParseError as e:
            logger.error(f"Failed to parse Fotolife response: {e}")
            return None

    def upload_image(
        self,
        image_data: BytesIO,
        filename: str,
        title: Optional[str] = None,
        timeout: int = 30,
    ) -> Optional[str]:
        """Upload image to Hatena Fotolife

        Args:
            image_data: Image data as BytesIO
            filename: Filename for the image
            title: Image title (defaults to filename)
            timeout: Request timeout in seconds

        Returns:
            Dict with syntax/url or None on failure
        """
        if not all([self.consumer_key, self.consumer_secret, self.access_token, self.access_token_secret]):
            logger.error("Cannot upload to Fotolife - OAuth credentials missing")
            return None

        try:
            image_title = title or filename

            # Create OAuth1 session
            oauth = OAuth1(
                self.consumer_key,
                client_secret=self.consumer_secret,
                resource_owner_key=self.access_token,
                resource_owner_secret=self.access_token_secret,
            )

            # Create upload XML
            xml_payload = self._create_upload_xml(
                title=image_title,
                image_data=image_data.getvalue()
            )

            # Upload to Fotolife
            logger.info(f"Uploading image to Hatena Fotolife: {image_title}")
            headers = {
                "Content-Type": "application/atom+xml;type=entry;charset=utf-8"
            }

            response = requests.post(
                self.post_uri,
                data=xml_payload,
                headers=headers,
                auth=oauth,
                timeout=timeout,
            )

            response.raise_for_status()

            # Extract image info from response
            image_info = self._extract_image_info(response.text)

            if image_info:
                logger.info(f"Image uploaded successfully: {image_info}")
                return image_info

            logger.warning("Upload succeeded but could not extract image info")
            return None

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to upload to Hatena Fotolife: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response: {e.response.text}")
            return None
