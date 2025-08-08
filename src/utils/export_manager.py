"""
Export manager for translation results and batch processing data
"""

import csv
import json

try:
    import defusedxml.ElementTree as ET
except ImportError:
    # Fallback to standard library with security warning
    import warnings
    import xml.etree.ElementTree as ET

    warnings.warn(
        "defusedxml not available. Using xml.etree.ElementTree which may be vulnerable to XML attacks",
        UserWarning,
        stacklevel=2,
    )
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.core.batch_processor import BatchJob
from src.models.translation import Translation
from src.utils.logger import logger


class ExportManager:
    """Manager for exporting translation data in various formats"""

    def __init__(self):
        self.supported_formats = {
            "json": self._export_json,
            "csv": self._export_csv,
            "txt": self._export_txt,
            "xml": self._export_xml,
            "html": self._export_html,
        }

    def export_translations(
        self, translations: List[Translation], file_path: str, format_type: str = "json"
    ) -> bool:
        """Export translations to specified format"""
        try:
            if format_type not in self.supported_formats:
                logger.error(f"Unsupported export format: {format_type}")
                return False

            # Ensure directory exists
            Path(file_path).parent.mkdir(parents=True, exist_ok=True)

            # Export using the appropriate method
            export_func = self.supported_formats[format_type]
            export_func(translations, file_path)

            logger.info(f"Exported {len(translations)} translations to {file_path}")
            return True

        except Exception as e:
            logger.error(f"Export failed: {e}")
            return False

    def export_batch_job(
        self,
        batch_job: BatchJob,
        file_path: str,
        format_type: str = "json",
        include_metadata: bool = True,
    ) -> bool:
        """Export batch job results with metadata"""
        try:
            # Get successful translations
            translations = [
                item.result
                for item in batch_job.items
                if item.result and item.status.value == "completed"
            ]

            if include_metadata:
                return self._export_batch_with_metadata(
                    batch_job, translations, file_path, format_type
                )
            else:
                return self.export_translations(translations, file_path, format_type)

        except Exception as e:
            logger.error(f"Batch export failed: {e}")
            return False

    def _export_json(self, translations: List[Translation], file_path: str) -> None:
        """Export to JSON format"""
        data = {
            "export_info": {
                "timestamp": datetime.now().isoformat(),
                "count": len(translations),
                "format": "json",
                "version": "2.0",
            },
            "translations": [self._translation_to_dict(t) for t in translations],
        }

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _export_csv(self, translations: List[Translation], file_path: str) -> None:
        """Export to CSV format"""
        with open(file_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)

            # Header
            writer.writerow(
                [
                    "Timestamp",
                    "Original Text",
                    "Translated Text",
                    "Source Language",
                    "Target Language",
                    "Confidence",
                ]
            )

            # Data rows
            for t in translations:
                writer.writerow(
                    [
                        t.timestamp.isoformat() if t.timestamp else "",
                        t.original_text,
                        t.translated_text,
                        t.source_language,
                        t.target_language,
                        t.confidence if t.confidence is not None else "",
                    ]
                )

    def _export_txt(self, translations: List[Translation], file_path: str) -> None:
        """Export to plain text format"""
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(f"Screen Translator Export - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total translations: {len(translations)}\n")
            f.write("=" * 60 + "\n\n")

            for i, t in enumerate(translations, 1):
                f.write(f"Translation #{i}\n")
                f.write(f"Time: {t.timestamp.strftime('%H:%M:%S') if t.timestamp else 'Unknown'}\n")
                f.write(f"Language: {t.source_language} → {t.target_language}\n")
                if t.confidence is not None:
                    f.write(f"Confidence: {t.confidence:.1f}%\n")
                f.write(f"\nOriginal:\n{t.original_text}\n")
                f.write(f"\nTranslation:\n{t.translated_text}\n")
                f.write("-" * 40 + "\n\n")

    def _export_xml(self, translations: List[Translation], file_path: str) -> None:
        """Export to XML format"""
        root = ET.Element("screen_translator_export")

        # Metadata
        metadata = ET.SubElement(root, "metadata")
        ET.SubElement(metadata, "timestamp").text = datetime.now().isoformat()
        ET.SubElement(metadata, "count").text = str(len(translations))
        ET.SubElement(metadata, "format").text = "xml"
        ET.SubElement(metadata, "version").text = "2.0"

        # Translations
        translations_elem = ET.SubElement(root, "translations")

        for t in translations:
            trans_elem = ET.SubElement(translations_elem, "translation")

            if t.timestamp:
                ET.SubElement(trans_elem, "timestamp").text = t.timestamp.isoformat()
            ET.SubElement(trans_elem, "original_text").text = t.original_text
            ET.SubElement(trans_elem, "translated_text").text = t.translated_text
            ET.SubElement(trans_elem, "source_language").text = t.source_language
            ET.SubElement(trans_elem, "target_language").text = t.target_language
            if t.confidence is not None:
                ET.SubElement(trans_elem, "confidence").text = str(t.confidence)

        # Write to file
        tree = ET.ElementTree(root)
        ET.indent(tree, space="  ", level=0)
        tree.write(file_path, encoding="utf-8", xml_declaration=True)

    def _export_html(self, translations: List[Translation], file_path: str) -> None:
        """Export to HTML format"""
        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Screen Translator Export</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background-color: #f5f5f5; padding: 20px; border-radius: 5px; margin-bottom: 20px; }}
        .translation {{ border: 1px solid #ddd; margin-bottom: 15px; padding: 15px; border-radius: 5px; }}
        .original {{ background-color: #e3f2fd; padding: 10px; margin-bottom: 10px; border-radius: 3px; }}
        .translated {{ background-color: #e8f5e8; padding: 10px; border-radius: 3px; }}
        .metadata {{ font-size: 0.9em; color: #666; margin-bottom: 10px; }}
        .confidence {{ color: #ff9800; font-weight: bold; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Screen Translator Export</h1>
        <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p>Total translations: {len(translations)}</p>
    </div>
"""

        for i, t in enumerate(translations, 1):
            confidence_html = (
                f" | Confidence: <span class='confidence'>{t.confidence:.1f}%</span>"
                if t.confidence is not None
                else ""
            )
            time_html = t.timestamp.strftime("%H:%M:%S") if t.timestamp else "Unknown"

            html_content += f"""
    <div class="translation">
        <div class="metadata">
            #{i} | {time_html} | {t.source_language} → {t.target_language}{confidence_html}
        </div>
        <div class="original">
            <strong>Original:</strong><br>
            {self._escape_html(t.original_text)}
        </div>
        <div class="translated">
            <strong>Translation:</strong><br>
            {self._escape_html(t.translated_text)}
        </div>
    </div>
"""

        html_content += """
</body>
</html>"""

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(html_content)

    def _export_batch_with_metadata(
        self, batch_job: BatchJob, translations: List[Translation], file_path: str, format_type: str
    ) -> bool:
        """Export batch job with full metadata"""
        if format_type == "json":
            return self._export_batch_json(batch_job, translations, file_path)
        elif format_type == "html":
            return self._export_batch_html(batch_job, translations, file_path)
        else:
            # For other formats, just export translations without batch metadata
            return self.export_translations(translations, file_path, format_type)

    def _export_batch_json(
        self, batch_job: BatchJob, translations: List[Translation], file_path: str
    ) -> bool:
        """Export batch job to JSON with full metadata"""
        try:
            # Convert batch job to dict
            job_dict = {
                "id": batch_job.id,
                "name": batch_job.name,
                "status": batch_job.status.value,
                "total_items": batch_job.total_items,
                "completed_items": batch_job.completed_items,
                "failed_items": batch_job.failed_items,
                "success_rate": batch_job.success_rate,
                "created_at": batch_job.created_at.isoformat(),
                "started_at": batch_job.started_at.isoformat() if batch_job.started_at else None,
                "completed_at": (
                    batch_job.completed_at.isoformat() if batch_job.completed_at else None
                ),
            }

            data = {
                "export_info": {
                    "timestamp": datetime.now().isoformat(),
                    "type": "batch_job",
                    "format": "json",
                    "version": "2.0",
                },
                "batch_job": job_dict,
                "translations": [self._translation_to_dict(t) for t in translations],
                "failed_items": [
                    {"id": item.id, "error": item.error, "processing_time": item.processing_time}
                    for item in batch_job.items
                    if item.status.value == "failed"
                ],
            }

            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            return True

        except Exception as e:
            logger.error(f"Batch JSON export failed: {e}")
            return False

    def _export_batch_html(
        self, batch_job: BatchJob, translations: List[Translation], file_path: str
    ) -> bool:
        """Export batch job to HTML with full metadata"""
        try:
            processing_time = ""
            if batch_job.started_at and batch_job.completed_at:
                duration = batch_job.completed_at - batch_job.started_at
                processing_time = f"Processing time: {duration.total_seconds():.1f} seconds"

            html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Batch Job Export - {batch_job.name}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background-color: #f5f5f5; padding: 20px; border-radius: 5px; margin-bottom: 20px; }}
        .batch-info {{ background-color: #e3f2fd; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
        .stats {{ display: flex; gap: 20px; margin: 10px 0; }}
        .stat {{ text-align: center; }}
        .stat-value {{ font-size: 1.5em; font-weight: bold; color: #1976d2; }}
        .translation {{ border: 1px solid #ddd; margin-bottom: 15px; padding: 15px; border-radius: 5px; }}
        .original {{ background-color: #fff3e0; padding: 10px; margin-bottom: 10px; border-radius: 3px; }}
        .translated {{ background-color: #e8f5e8; padding: 10px; border-radius: 3px; }}
        .metadata {{ font-size: 0.9em; color: #666; margin-bottom: 10px; }}
        .success {{ color: #4caf50; }}
        .error {{ color: #f44336; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Batch Job Export</h1>
        <h2>{batch_job.name}</h2>
        <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>

    <div class="batch-info">
        <h3>Job Information</h3>
        <p><strong>Job ID:</strong> {batch_job.id}</p>
        <p><strong>Status:</strong> <span class="{'success' if batch_job.status.value == 'completed' else 'error'}">{batch_job.status.value.title()}</span></p>
        <p><strong>Created:</strong> {batch_job.created_at.strftime('%Y-%m-%d %H:%M:%S')}</p>
        {f"<p><strong>{processing_time}</strong></p>" if processing_time else ""}

        <div class="stats">
            <div class="stat">
                <div class="stat-value">{batch_job.total_items}</div>
                <div>Total Items</div>
            </div>
            <div class="stat">
                <div class="stat-value success">{batch_job.completed_items}</div>
                <div>Successful</div>
            </div>
            <div class="stat">
                <div class="stat-value error">{batch_job.failed_items}</div>
                <div>Failed</div>
            </div>
            <div class="stat">
                <div class="stat-value">{batch_job.success_rate:.1f}%</div>
                <div>Success Rate</div>
            </div>
        </div>
    </div>

    <h3>Successful Translations ({len(translations)})</h3>
"""

            for i, t in enumerate(translations, 1):
                confidence_html = (
                    f" | Confidence: {t.confidence:.1f}%" if t.confidence is not None else ""
                )
                time_html = t.timestamp.strftime("%H:%M:%S") if t.timestamp else "Unknown"

                html_content += f"""
    <div class="translation">
        <div class="metadata">
            #{i} | {time_html} | {t.source_language} → {t.target_language}{confidence_html}
        </div>
        <div class="original">
            <strong>Original:</strong><br>
            {self._escape_html(t.original_text)}
        </div>
        <div class="translated">
            <strong>Translation:</strong><br>
            {self._escape_html(t.translated_text)}
        </div>
    </div>
"""

            # Add failed items section
            failed_items = [item for item in batch_job.items if item.status.value == "failed"]
            if failed_items:
                html_content += f"""
    <h3>Failed Items ({len(failed_items)})</h3>
    <div style="background-color: #ffebee; padding: 15px; border-radius: 5px;">
"""
                for item in failed_items:
                    html_content += f"""
        <div style="margin-bottom: 10px; padding: 10px; background-color: white; border-radius: 3px;">
            <strong>Item ID:</strong> {item.id}<br>
            <strong>Error:</strong> {self._escape_html(item.error or 'Unknown error')}<br>
            <strong>Processing time:</strong> {item.processing_time:.2f}s
        </div>
"""
                html_content += "</div>"

            html_content += """
</body>
</html>"""

            with open(file_path, "w", encoding="utf-8") as f:
                f.write(html_content)

            return True

        except Exception as e:
            logger.error(f"Batch HTML export failed: {e}")
            return False

    def _translation_to_dict(self, translation: Translation) -> Dict[str, Any]:
        """Convert Translation object to dictionary"""
        return {
            "timestamp": translation.timestamp.isoformat() if translation.timestamp else None,
            "original_text": translation.original_text,
            "translated_text": translation.translated_text,
            "source_language": translation.source_language,
            "target_language": translation.target_language,
            "confidence": translation.confidence,
        }

    def _escape_html(self, text: str) -> str:
        """Escape HTML special characters"""
        if not text:
            return ""
        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#x27;")
        )

    def get_supported_formats(self) -> List[str]:
        """Get list of supported export formats"""
        return list(self.supported_formats.keys())

    def suggest_filename(
        self, base_name: str, format_type: str, include_timestamp: bool = True
    ) -> str:
        """Suggest a filename for export"""
        timestamp = datetime.now().strftime("_%Y%m%d_%H%M%S") if include_timestamp else ""
        return f"{base_name}{timestamp}.{format_type}"


# Convenience functions for quick exports
def export_translation_history(
    translations: List[Translation], directory: str = "exports"
) -> Optional[str]:
    """Quick export of translation history"""
    try:
        manager = ExportManager()
        Path(directory).mkdir(exist_ok=True)

        filename = manager.suggest_filename("translation_history", "json")
        file_path = Path(directory) / filename

        if manager.export_translations(translations, str(file_path)):
            return str(file_path)
        return None

    except Exception as e:
        logger.error(f"Quick export failed: {e}")
        return None


def export_batch_results(
    batch_job: BatchJob, directory: str = "exports", format_type: str = "html"
) -> Optional[str]:
    """Quick export of batch job results"""
    try:
        manager = ExportManager()
        Path(directory).mkdir(exist_ok=True)

        safe_name = "".join(
            c for c in batch_job.name if c.isalnum() or c in (" ", "-", "_")
        ).strip()
        filename = manager.suggest_filename(f"batch_{safe_name}", format_type)
        file_path = Path(directory) / filename

        if manager.export_batch_job(batch_job, str(file_path), format_type, include_metadata=True):
            return str(file_path)
        return None

    except Exception as e:
        logger.error(f"Quick batch export failed: {e}")
        return None
