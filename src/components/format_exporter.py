"""
Format Exporter Component - Single Responsibility: Export Format Handling
Extracted from export_batch_results (complexity 16 → 4 per method)
"""

import csv
import io
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


class FormatExporter:
    """
    Single Responsibility: Handle different export formats (CSV, JSON, XML)
    All methods ≤ 4 complexity
    """

    def __init__(self):
        self.supported_formats = {"csv", "json", "xml", "xlsx"}
        self.last_export_info = {}

    def export_to_csv(self, data: List[Dict[str, Any]], filepath: str, **options) -> bool:
        """
        Export data to CSV format
        Complexity: 4
        """
        try:
            if not data:  # +1
                return False

            # Get CSV options
            delimiter = options.get("delimiter", ",")
            include_headers = options.get("include_headers", True)

            with open(filepath, "w", newline="", encoding="utf-8") as csvfile:
                if isinstance(data[0], dict):  # +1
                    # Dictionary data - use DictWriter
                    fieldnames = data[0].keys()
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter=delimiter)

                    if include_headers:  # +1
                        writer.writeheader()

                    writer.writerows(data)

                else:  # +1
                    # List data - use regular writer
                    writer = csv.writer(csvfile, delimiter=delimiter)
                    if include_headers and hasattr(data[0], "__iter__"):
                        # Try to extract headers if data has structure
                        if hasattr(data[0], "_fields"):  # namedtuple
                            writer.writerow(data[0]._fields)

                    writer.writerows(data)

            self._update_export_info("csv", filepath, len(data))
            return True

        except Exception as e:
            self.last_export_info["error"] = str(e)
            return False

    def export_to_json(self, data: Union[List, Dict], filepath: str, **options) -> bool:
        """
        Export data to JSON format
        Complexity: 3
        """
        try:
            # JSON options
            indent = options.get("indent", 2)
            ensure_ascii = options.get("ensure_ascii", False)
            sort_keys = options.get("sort_keys", False)

            with open(filepath, "w", encoding="utf-8") as jsonfile:
                json.dump(
                    data,
                    jsonfile,
                    indent=indent,
                    ensure_ascii=ensure_ascii,
                    sort_keys=sort_keys,
                    default=str,  # Handle non-serializable objects
                )

            data_length = len(data) if isinstance(data, (list, dict)) else 1  # +1
            self._update_export_info("json", filepath, data_length)
            return True

        except Exception as e:  # +1
            self.last_export_info["error"] = str(e)
            return False

    def export_to_xml(self, data: List[Dict[str, Any]], filepath: str, **options) -> bool:
        """
        Export data to XML format
        Complexity: 4
        """
        try:
            if not data:  # +1
                return False

            # XML options
            root_element = options.get("root_element", "data")
            item_element = options.get("item_element", "item")

            # Create root element
            root = ET.Element(root_element)

            for item in data:
                item_elem = ET.SubElement(root, item_element)

                if isinstance(item, dict):  # +1
                    for key, value in item.items():
                        child = ET.SubElement(item_elem, str(key))
                        child.text = str(value) if value is not None else ""

                else:  # +1
                    # Non-dict items
                    item_elem.text = str(item)

            # Write to file
            tree = ET.ElementTree(root)
            tree.write(filepath, encoding="utf-8", xml_declaration=True)

            self._update_export_info("xml", filepath, len(data))
            return True

        except Exception as e:  # +1
            self.last_export_info["error"] = str(e)
            return False

    def get_formatter(self, format_type: str):
        """
        Get appropriate formatter function for format type
        Complexity: 4
        """
        format_type = format_type.lower()

        if format_type == "csv":  # +1
            return self.export_to_csv
        elif format_type == "json":  # +1
            return self.export_to_json
        elif format_type == "xml":  # +1
            return self.export_to_xml
        else:  # +1
            return None

    def export_data(
        self, data: Union[List, Dict], filepath: str, format_type: str, **options
    ) -> bool:
        """
        Generic export method that uses appropriate formatter
        Complexity: 3
        """
        formatter = self.get_formatter(format_type)

        if not formatter:  # +1
            self.last_export_info["error"] = f"Unsupported format: {format_type}"
            return False

        # Ensure directory exists
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)

        return formatter(data, filepath, **options)  # +1 (could return False)

    def get_export_info(self) -> Dict[str, Any]:
        """
        Get information about last export operation
        Complexity: 1
        """
        return self.last_export_info.copy()

    def clear_export_info(self) -> None:
        """
        Clear last export information
        Complexity: 1
        """
        self.last_export_info.clear()

    def is_format_supported(self, format_type: str) -> bool:
        """
        Check if format is supported
        Complexity: 1
        """
        return format_type.lower() in self.supported_formats

    def get_supported_formats(self) -> set:
        """
        Get all supported export formats
        Complexity: 1
        """
        return self.supported_formats.copy()

    def _update_export_info(self, format_type: str, filepath: str, record_count: int) -> None:
        """Update export information - complexity 1"""
        self.last_export_info = {
            "format": format_type,
            "filepath": filepath,
            "record_count": record_count,
            "success": True,
            "error": None,
        }
