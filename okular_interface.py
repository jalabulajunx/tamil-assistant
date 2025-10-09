#!/usr/bin/env python3
"""
D-Bus interface to communicate with Okular
"""

import dbus
import subprocess
import logging
from pdf2image import convert_from_path
from PIL import Image
import os

class OkularInterface:
    def __init__(self):
        self.bus = dbus.SessionBus()
        self.okular_service = None
        self.okular_object = None
        self.logger = logging.getLogger('OkularInterface')

    def find_okular(self):
        """Find running Okular instance via D-Bus"""
        try:
            # List all services
            proxy = self.bus.get_object('org.freedesktop.DBus',
                                       '/org/freedesktop/DBus')
            dbus_interface = dbus.Interface(proxy, 'org.freedesktop.DBus')
            services = dbus_interface.ListNames()

            # Find okular service
            for service in services:
                if service.startswith('org.kde.okular'):
                    self.okular_service = service
                    self.okular_object = self.bus.get_object(service, '/okular')
                    self.logger.info(f"Found Okular service: {service}")
                    return True

            self.logger.warning("No Okular service found")
            return False
        except Exception as e:
            self.logger.error(f"Error finding Okular: {e}")
            return False

    def get_current_page(self):
        """Get current page number from Okular"""
        if not self.okular_service:
            if not self.find_okular():
                raise Exception("Okular not running")

        try:
            # Try different methods
            methods = [
                lambda: self.okular_object.currentPage(
                    dbus_interface='org.kde.okular'),
                lambda: int(subprocess.check_output([
                    'qdbus', self.okular_service, '/okular', 'currentPage'
                ]).decode().strip())
            ]

            for method in methods:
                try:
                    page = method()
                    page_num = int(page)
                    self.logger.info(f"Current page: {page_num}")
                    return page_num
                except:
                    continue

            raise Exception("Could not get current page")

        except Exception as e:
            raise Exception(f"Failed to get current page: {e}")

    def get_current_document(self):
        """Get current document path from Okular"""
        if not self.okular_service:
            if not self.find_okular():
                raise Exception("Okular not running")

        try:
            # Try different methods
            methods = [
                lambda: self.okular_object.currentDocument(
                    dbus_interface='org.kde.okular'),
                lambda: subprocess.check_output([
                    'qdbus', self.okular_service, '/okular', 'currentDocument'
                ]).decode().strip()
            ]

            for method in methods:
                try:
                    doc = method()
                    if doc and doc != '':
                        doc_path = str(doc)
                        self.logger.info(f"Current document: {doc_path}")
                        return doc_path
                except:
                    continue

            raise Exception("No document open")

        except Exception as e:
            raise Exception(f"Failed to get document: {e}")

    def get_selected_text(self):
        """Get selected text from Okular (if available)"""
        try:
            # This is trickier - may need clipboard workaround
            # For now, return from clipboard
            import subprocess
            text = subprocess.check_output(['xclip', '-o', '-selection', 'primary']).decode('utf-8')
            return text.strip()
        except:
            return ""

    def render_page_to_image(self, pdf_path, page_number):
        """Render a PDF page to image"""
        try:
            self.logger.info(f"Rendering page {page_number} from PDF: {os.path.basename(pdf_path)}")
            
            # Convert PDF page to image (1-indexed for pdf2image)
            images = convert_from_path(
                pdf_path,
                first_page=page_number,  # Okular uses 0-indexed, pdf2image uses 1-indexed
                last_page=page_number,
                dpi=200
            )

            if images:
                self.logger.info(f"Successfully rendered page {page_number} to image")
                return images[0]
            else:
                raise Exception("Failed to render page")

        except Exception as e:
            self.logger.error(f"Failed to render page: {e}")
            raise Exception(f"Failed to render page: {e}")
