#!/usr/bin/env python3
"""
SOAR Ransomware Lab - IOC Generator Service
Infrastructure adapter for generating and persisting IOCs
"""

import json
from typing import Dict, Any

from soar_lab.domain.ports import FileSystemInterface, IOCGenerator


class IOCPackageGenerator:
    """Service for generating IOC packages with injected dependencies."""

    def __init__(self, ioc_generator: IOCGenerator, file_system: FileSystemInterface):
        """
        Initialize the IOC package generator.

        Args:
            ioc_generator: Domain IOCGenerator instance (required).
            file_system: File system interface for writing output files (required).
        """
        if not ioc_generator:
            raise ValueError("ioc_generator is required for IOCPackageGenerator")
        if not file_system:
            raise ValueError("file_system is required for IOCPackageGenerator")
        self.ioc_generator = ioc_generator
        self.file_system = file_system

    def create_ioc_package(self, output_file: str = None, count: int = 5) -> Dict[str, Any]:
        """
        Create a JSON package of simulated IOCs using domain IOCGenerator.

        Args:
            output_file: Output file path for the IOC package
            count: Number of IOCs to generate per type

        Returns:
            Dict with malicious and benign IOCs
        """
        iocs = self.ioc_generator.create_ioc_package(count)

        if output_file and self.file_system:
            self.file_system.write_file(output_file, json.dumps(iocs, indent=4))

        return iocs


# Backward compatibility: module-level function for existing code
def create_ioc_package(output_file: str, count: int = 5, file_system: FileSystemInterface = None,
                       ioc_generator: IOCGenerator = None) -> Dict[str, Any]:
    """
    Create a JSON package of simulated IOCs using domain IOCGenerator.

    Args:
        output_file: Output file path for the IOC package
        count: Number of IOCs to generate per type
        file_system: File system interface for writing output (required)
        ioc_generator: Domain IOCGenerator instance (injected dependency, required)

    Returns:
        Dict with malicious and benign IOCs
    """
    if not ioc_generator:
        raise ValueError("ioc_generator is required for create_ioc_package")
    if not file_system:
        raise ValueError("file_system is required for create_ioc_package")

    generator = IOCPackageGenerator(ioc_generator, file_system)
    return generator.create_ioc_package(output_file, count)
