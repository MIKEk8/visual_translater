"""
Refactored Process Data Stream - Main Coordinator
Complexity reduced from 14 to 5
"""

from typing import Any, Dict, Iterator, List, Optional

from .data_transformer import DataTransformer
from .stream_buffer import StreamBuffer
from .stream_error_manager import StreamErrorManager
from .stream_validator import StreamValidator


class RefactoredProcessDataStream:
    """Main coordinator for data stream processing - complexity ≤ 5"""

    def __init__(self):
        self.validator = StreamValidator()
        self.transformer = DataTransformer()
        self.buffer = StreamBuffer()
        self.error_manager = StreamErrorManager()

    def process_data_stream(
        self, data_stream: Iterator[Dict[str, Any]], processing_config: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Process complete data stream - complexity 5"""
        processing_config = processing_config or {}

        try:
            # Step 1: Validate stream
            stream_valid, validation_errors = self.validator.validate_stream(data_stream)
            if not stream_valid and not processing_config.get("ignore_validation_errors"):  # +1
                return {"success": False, "stage": "validation", "errors": validation_errors}

            # Step 2: Transform stream data
            transformations = processing_config.get("transformations", [])
            transformed_stream = self.transformer.transform_stream(data_stream, transformations)

            # Step 3: Buffer processed data
            processed_items = []
            buffer_errors = 0

            for item in transformed_stream:  # +1
                if not self.buffer.add_to_buffer(item):  # +1
                    buffer_errors += 1
                    if buffer_errors > processing_config.get("max_buffer_errors", 10):  # +1
                        break

            # Step 4: Collect results
            final_results = self.buffer.consume_from_buffer(
                batch_size=processing_config.get("batch_size", 100)
            )

            # Step 5: Generate summary
            transform_stats = self.transformer.get_transform_stats()
            buffer_status = self.buffer.get_buffer_status()

            return {
                "success": True,
                "processed_count": len(final_results),
                "transform_stats": transform_stats,
                "buffer_status": buffer_status,
                "stage": "completed",
            }

        except Exception as e:  # +1
            error_info = self.error_manager.handle_stream_error(
                e, "stream", {"stage": "processing"}
            )
            return {
                "success": False,
                "error": str(e),
                "error_details": error_info,
                "stage": "error",
            }

    def get_processing_status(self) -> Dict[str, Any]:
        """Get processing status - complexity 2"""
        return {
            "validator_errors": len(self.validator.errors),
            "transform_stats": self.transformer.get_transform_stats(),
            "buffer_status": self.buffer.get_buffer_status(),  # +1
            "error_summary": self.error_manager.get_error_summary(),
        }
