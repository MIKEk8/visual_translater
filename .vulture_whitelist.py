# Vulture whitelist for Screen Translator v2.0
# This file contains patterns and names that should be ignored by Vulture

# Interface method parameters - these are abstract methods with unused parameters
language_code  # Abstract method parameter in IOCRProcessor.set_language()
interface_type  # Abstract method parameter in IDIContainer methods
implementation_type  # Abstract method parameter in IDIContainer.register_singleton()
days  # Abstract method parameter in IScreenshotRepository.delete_old()

# Import checks that are only used for availability detection
defusedxml  # Security import check in batch_export_manager.py